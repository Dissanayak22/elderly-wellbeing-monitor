import kagglehub

path = kagglehub.dataset_download(
    "msambare/fer2013",
    output_dir=r"D:\elderly-wellbeing-monitor\ai\datasets\fer2013",
)

print("Dataset downloaded to:", path)