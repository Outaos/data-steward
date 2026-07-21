from pathlib import Path

DISTRICT_FOLDERS = [
    "DCC (Cariboo-Chilcotin)",
    "DCS (Cascades)",
    "DKA (Thompson Rivers)",
    "DMH (100 Mile House)",
    "DOS (Okanagan Shuswap)",
    "DQU (Quesnel)",
    "DRM (Rocky Mountains)",
    "DSE (Selkirk)",
    "SA (South Area)",
    "BC (Province-wide Data)",
]


def create_district_folders(main_folder: str) -> None:
    """Create district folders inside the specified main folder."""

    parent_folder = Path(main_folder.strip().strip('"'))

    if not parent_folder.exists():
        raise FileNotFoundError(
            f"The main folder does not exist:\n{parent_folder}"
        )

    if not parent_folder.is_dir():
        raise NotADirectoryError(
            f"The supplied path is not a folder:\n{parent_folder}"
        )

    for folder_name in DISTRICT_FOLDERS:
        new_folder = parent_folder / folder_name
        new_folder.mkdir(exist_ok=True)
        print(f"Created or already exists: {new_folder}")

    print("\nDistrict folder creation completed.")


if __name__ == "__main__":
    main_folder_input = input(
        "Enter the full path to the main folder: "
    )

    try:
        create_district_folders(main_folder_input)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as error:
        print(f"\nError: {error}")