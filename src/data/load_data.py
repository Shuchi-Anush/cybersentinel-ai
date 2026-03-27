import pandas as pd

# Dataset location
from src.core.paths import DATA_DIR as BASE_DATA_DIR

DATA_DIR = BASE_DATA_DIR / "raw" / "CICIDS2017"

# Scenario split to prevent leakage
TRAIN_FILES = [
    "Monday-WorkingHours.pcap_ISCX.csv",
    "Tuesday-WorkingHours.pcap_ISCX.csv",
    "Wednesday-workingHours.pcap_ISCX.csv",
]

TEST_FILES = [
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
]


def load_files(file_list):
    """Load multiple CSV files and combine them"""

    dfs = []

    for file in file_list:
        path = DATA_DIR / file

        if not path.exists():
            raise FileNotFoundError(f"Missing dataset file: {path}")

        df = pd.read_csv(path)

        print(f"Loaded {file} → {len(df)} rows")

        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    return combined


def load_cic_dataset():
    """Load CICIDS dataset with scenario split"""

    print("\nLoading training scenarios...")
    train_df = load_files(TRAIN_FILES)

    print("\nLoading testing scenarios...")
    test_df = load_files(TEST_FILES)

    X_train = train_df.drop("Label", axis=1)
    y_train = train_df["Label"]

    X_test = test_df.drop("Label", axis=1)
    y_test = test_df["Label"]

    return X_train, X_test, y_train, y_test
