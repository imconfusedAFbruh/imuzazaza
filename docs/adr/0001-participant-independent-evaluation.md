# Partition by participant before creating windows

The paper targets held-out evaluation on the Sept. 24-25 recordings, while earlier sessions may supply training data. Assign every recording from one participant across all dates to a single partition before creating windows, and fit calibration, normalization, and model parameters using training data only. This sacrifices the convenience of splitting by recording or date to prevent participant overlap; final test data remains untouched during development, and cross-date identity mapping is a prerequisite for assigning partitions.
