from typing import List, Iterator
import numpy as np

from torch.utils.data.sampler import Sampler


class BalanceClassSampler(Sampler):
    """
    Abstraction over data sampler. Allows you to create stratified sample
    on unbalanced classes.
    """

    def __init__(self, labels: List[int], mode: str = "downsampling"):
        """
        Args:
            labels (List[int]): list of class label
                for each elem in the datasety
            mode (str): Strategy to balance classes.
                Must be one of [downsampling, upsampling]
        """
        super().__init__(labels)

        labels = np.array(labels)
        samples_per_class = {
            label: (labels == label).sum()
            for label in set(labels)
        }

        self.lbl2idx = {
            label: np.arange(len(labels))[labels == label].tolist()
            for label in set(labels)
        }

        if isinstance(mode, int) or mode == "upsampling":
            samples_per_class = mode \
                if isinstance(mode, int) \
                else max(samples_per_class.values())
        else:
            samples_per_class = min(samples_per_class.values())

        self.labels = labels
        self.samples_per_class = samples_per_class
        self.length = self.samples_per_class * len(set(labels))

    def __iter__(self) -> Iterator[int]:
        """
        Yields:
            indices of stratified sample
        """
        indices = []
        for key in sorted(self.lbl2idx):
            replace_ = self.samples_per_class > len(self.lbl2idx[key])
            indices += np.random.choice(
                self.lbl2idx[key], self.samples_per_class, replace=replace_
            ).tolist()
        assert (len(indices) == self.length)
        np.random.shuffle(indices)

        return iter(indices)

    def __len__(self) -> int:
        """
        Returns:
             length of result sample
        """
        return self.length


class MiniEpochSampler(Sampler):
    r"""Sample indices by ``batches_per_epoch`` in one epoch

    Args:
        data_len (int): Size of the dataset
        batches_per_epoch (int): Size of batches by one epoch
        drop_last (bool): If ``True``, sampler will drop the last batches if
            its size would be less than ``batches_per_epoch``
        shuffle (str): one of  ``["always", "real_epoch", None]``.
            The sampler will shuffle indices
            > "per_mini_epoch" -- every mini epoch (every ``__iter__`` call)
            > "per_epoch" -- every real epoch
            > None -- don't shuffle

    Example:
        >>> MiniEpochSampler(len(dataset), batches_per_epoch=100)
        >>> MiniEpochSampler(len(dataset), batches_per_epoch=100, \
            drop_last=True)
        >>> MiniEpochSampler(len(dataset), batches_per_epoch=100, \
            shuffle="per_epoch")
    """

    def __init__(
        self,
        data_len: int,
        batches_per_epoch: int,
        drop_last: bool = False,
        shuffle: str = None
    ):
        super().__init__(None)

        self.data_len = int(data_len)
        self.epoch_len = int(batches_per_epoch)

        self.steps = int(data_len / self.epoch_len)
        self.state_i = 0

        has_reminder = data_len - self.steps * batches_per_epoch > 0
        if self.steps == 0:
            self.divider = 1
        elif has_reminder and not drop_last:
            self.divider = self.steps + 1
        else:
            self.divider = self.steps

        self.indices = np.arange(self.data_len)

        if not (shuffle is None or shuffle in ["per_mini_epoch", "per_epoch"]):
            raise ValueError(
                f"Shuffle must be one of ['per_mini_epoch', 'per_epoch']. "
                f"Got {shuffle}"
            )
        self.shuffle_type = shuffle

    def shuffle(self):
        if self.shuffle_type == "per_mini_epoch" or \
                (self.shuffle_type == "per_epoch" and self.state_i == 0):
            np.random.shuffle(self.indices)

    def __iter__(self) -> Iterator[int]:
        self.state_i = self.state_i % self.divider
        self.shuffle()

        start = self.state_i * self.epoch_len
        stop = self.data_len if (self.state_i == self.steps) \
            else (self.state_i + 1) * self.epoch_len

        indices = self.indices[start:stop].tolist()

        self.state_i += 1
        return iter(indices)

    def __len__(self) -> int:
        return self.epoch_len
