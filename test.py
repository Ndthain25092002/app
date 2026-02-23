import os

def print_tree(folder, prefix=""):
    """Đệ quy in cấu trúc thư mục dạng cây"""
    # Lấy danh sách file và folder, sắp xếp alphabet
    items = sorted(os.listdir(folder))
    for i, item in enumerate(items):
        path = os.path.join(folder, item)
        # Xác định ký hiệu nhánh cuối cùng hay còn nhánh
        connector = "└── " if i == len(items) - 1 else "├── "
        print(prefix + connector + item)
        if os.path.isdir(path):
            # Nếu là thư mục, gọi đệ quy với prefix mới
            extension = "    " if i == len(items) - 1 else "│   "
            print_tree(path, prefix + extension)

# Folder cần in (hiện tại)
root_folder = os.getcwd()
print(root_folder)
print_tree(root_folder)
