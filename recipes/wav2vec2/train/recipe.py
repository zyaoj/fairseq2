# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

from typing import final

from torch import Tensor
from typing_extensions import override

from fairseq2.datasets import SequenceBatch, SyncMode, register_dataset_family
from fairseq2.evaluator import EvalUnit
from fairseq2.gang import Gangs
from fairseq2.metrics import MetricBag
from fairseq2.model import Model
from fairseq2.recipe.base import RecipeContext, TrainRecipe
from fairseq2.runtime.dependency import DependencyContainer
from fairseq2.trainer import Trainer, TrainUnit

from .criterion import Wav2Vec2Criterion
from .data import (
    WAV2VEC2_DATASET,
    Wav2Vec2TrainDataset,
    Wav2Vec2TrainDatasetConfig,
    open_wav2vec2_train_dataset,
)
from .default_config import Wav2Vec2TrainConfig


@final
class Wav2Vec2TrainRecipe(TrainRecipe):
    @override
    def register(self, container: DependencyContainer) -> None:
        register_dataset_family(
            container,
            WAV2VEC2_DATASET,
            Wav2Vec2TrainDataset,
            Wav2Vec2TrainDatasetConfig,
            opener=open_wav2vec2_train_dataset,
        )

    @override
    def create_trainer(self, context: RecipeContext) -> Trainer:
        config = context.config_as(Wav2Vec2TrainConfig)

        # Initialize criterion - ORIGINAL: _train.py lines 235-237
        criterion = Wav2Vec2Criterion(
            context.model,
            config.loss.diversity_loss_weight,
            config.loss.feature_penalty_weight,
        )

        # Initialize train unit - ORIGINAL: _train.py line 239
        unit = Wav2Vec2TrainUnit(criterion, context.gangs)
        dataset = context.dataset_as(Wav2Vec2TrainDataset)

        # ORIGINAL: _train.py line 214 - seed += 1 after manual_seed
        # v0.5 handles manual_seed separately by advancing internally (see the seed= argument in create_reader())

        # Create data reader - ORIGINAL: _train.py lines 258-264
        data_reader = dataset.create_reader(
            config.dataset.train_split,
            context.gangs,
            min_audio_len=config.dataset.min_audio_len,
            max_audio_len=config.dataset.max_audio_len,
            # Batching parameters - ORIGINAL: v0.4 batching setup
            batching_strategy=config.dataset.batching_strategy,
            batch_size=config.dataset.batch_size,
            max_num_elements=config.dataset.max_num_elements,
            # Audio processing parameters - ORIGINAL: SpeechReadOptions
            dtype=config.trainer.dtype,
            normalize_audio=config.dataset.normalize_audio,
            use_fbank=config.dataset.use_fbank,
            no_padding=config.dataset.no_padding,
            npc=config.dataset.npc,
            # SpecAugment parameters - ORIGINAL: SpeechReadOptions
            spec_aug_p=config.dataset.spec_aug_p,
            spec_aug_freq_mask_param=config.dataset.spec_aug_freq_mask_param,
            spec_aug_time_mask_param=config.dataset.spec_aug_time_mask_param,
            # Shuffling and performance parameters - ORIGINAL: DataReadOptions
            example_shuffle_window=config.dataset.example_shuffle_window,
            batch_shuffle_window=config.dataset.batch_shuffle_window,
            num_accumulate=config.trainer.grad_accumulation.num_batches,
            num_prefetch=config.dataset.num_prefetch,
            drop_remainder=config.dataset.drop_remainder,
            sync_batches=config.dataset.sync_batches,
            sync_mode=config.dataset.sync_mode,
            seed=context.next_seed(),  # TODO: (cirquit) - advancing the seed instead of setting it, point for numerical instability
            max_num_batches=config.dataset.max_num_batches,
            extras=config.dataset.extras,
        )

        # Initialize validation units - ORIGINAL: _train.py lines 268-305
        valid_units = []
        valid_data_readers = []

        if config.dataset.valid_split is not None:
            # Set extras for validation - ORIGINAL: line 271
            valid_extras = dict(config.dataset.extras)
            valid_extras["is_binarized"] = False

            # Support multiple validation splits - ORIGINAL: line 288
            valid_splits = config.dataset.valid_split.split(",")

            for split in valid_splits:
                # Create validation unit - ORIGINAL: line 290
                valid_unit = Wav2Vec2EvalUnit(criterion, context.gangs)
                valid_units.append(valid_unit)

                # Create validation data reader - ORIGINAL: lines 293-300
                valid_data_reader = dataset.create_reader(
                    split,
                    context.gangs,
                    min_audio_len=config.dataset.min_audio_len,
                    max_audio_len=config.dataset.max_audio_len,
                    # Batching parameters - same as training
                    batching_strategy=config.dataset.batching_strategy,
                    batch_size=config.dataset.batch_size,
                    max_num_elements=config.dataset.max_num_elements,
                    # Audio processing parameters - same as training
                    dtype=config.trainer.dtype,
                    normalize_audio=config.dataset.normalize_audio,
                    use_fbank=config.dataset.use_fbank,
                    no_padding=config.dataset.no_padding,
                    npc=config.dataset.npc,
                    # SpecAugment parameters - same as training
                    spec_aug_p=config.dataset.spec_aug_p,
                    spec_aug_freq_mask_param=config.dataset.spec_aug_freq_mask_param,
                    spec_aug_time_mask_param=config.dataset.spec_aug_time_mask_param,
                    # Validation-specific parameters - ORIGINAL: lines 272-284
                    example_shuffle_window=config.dataset.example_shuffle_window,  # ORIGINAL: line 278
                    batch_shuffle_window=1,  # No batch shuffling for validation
                    num_accumulate=config.trainer.grad_accumulation.num_batches,
                    num_prefetch=config.dataset.num_prefetch,
                    drop_remainder=config.dataset.drop_remainder,
                    sync_batches=config.dataset.sync_batches,
                    sync_mode=SyncMode.UNTIL_LAST,  # ORIGINAL: line 276 - Wait for all processes
                    seed=context.next_seed(),
                    max_num_batches=config.dataset.max_num_batches,
                    extras=valid_extras,
                )
                valid_data_readers.append(valid_data_reader)

        return context.create_trainer(
            unit, data_reader, valid_units, valid_data_readers
        )

    @property
    @override
    def config_kls(self) -> type[object]:
        return Wav2Vec2TrainConfig


@final
class Wav2Vec2TrainUnit(TrainUnit[SequenceBatch]):
    """wav2vec2 training unit.

    ORIGINAL: fairseq2:e9fbd6/src/fairseq2/recipes/wav2vec2/_train.py:239
    Similar to Wav2Vec2EvalUnit but for training
    """

    _criterion: Wav2Vec2Criterion
    _gangs: Gangs

    def __init__(self, criterion: Wav2Vec2Criterion, gangs: Gangs) -> None:
        # ORIGINAL: _train.py line 239 - Wav2Vec2TrainUnit(criterion, gangs)
        self._criterion = criterion
        self._gangs = gangs

    @override
    def __call__(
        self, batch: SequenceBatch, metric_bag: MetricBag
    ) -> tuple[Tensor, int]:
        # ORIGINAL: Similar to v0.4 pattern - criterion handles forward pass and metrics
        return self._criterion(batch, metric_bag)

    @property
    @override
    def model(self) -> Model:
        # ORIGINAL: Access model through criterion (matches v0.4 pattern)
        return self._criterion.model


@final
class Wav2Vec2EvalUnit(EvalUnit[SequenceBatch]):
    """wav2vec2 evaluation unit for validation during training.

    ORIGINAL: fairseq2:e9fbd6/src/fairseq2/recipes/wav2vec2/_eval.py:189-211
    Class: Wav2Vec2EvalUnit
    """

    _criterion: Wav2Vec2Criterion
    _gangs: Gangs

    def __init__(self, criterion: Wav2Vec2Criterion, gangs: Gangs) -> None:
        # ORIGINAL: _eval.py line 194 - Wav2Vec2EvalUnit(criterion, gangs)
        self._criterion = criterion
        self._gangs = gangs

    @override
    def __call__(self, batch: SequenceBatch, metric_bag: MetricBag) -> None:
        # ORIGINAL: _eval.py line 200-201 - Just call criterion with metric_bag
        self._criterion(batch, metric_bag)

    @property
    @override
    def model(self) -> Model:
        # ORIGINAL: _eval.py line 205-206 - Access model through criterion
        return self._criterion.model
