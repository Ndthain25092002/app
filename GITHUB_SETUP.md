# 🔒 Hướng dẫn Đẩy lên GitHub An Toàn

## ✅ Đã Hoàn Thành Các Biện Pháp Bảo Mật

### 1. **Xóa Hardcoded Secrets**
- ✅ `config.py`: Loại bỏ API key Tavily hardcoded
- ✅ `tavily_agent.py`: Loại bỏ fallback API key hardcoded
- ✅ Tất cả API keys giờ lấy từ biến môi trường

### 2. **Cấu Hình .gitignore**
- ✅ Ignore `.env` file (chứa tất cả secrets)
- ✅ Ignore `__pycache__/`, `*.db`, v.v.
- ✅ Cho phép `.env.example` (template safe)

### 3. **Tạo .env.example Template**
- ✅ Hướng dẫn người dùng cấu hình biến môi trường
- ✅ Không chứa real API keys

---

## 📋 Các Bước Đẩy lên GitHub

### Bước 1: Tạo Repository trên GitHub
1. Vào https://github.com/new
2. Tên repository: `app-2.0` (hoặc tên tùy ý)
3. **Chọn**: Private (an toàn hơn) hoặc Public
4. ❌ **KHÔNG** chọn "Initialize with README" (vì đã có)
5. Nhấn "Create repository"

### Bước 2: Thêm Remote URL
```powershell
cd C:\Users\PC\Desktop\app-2.0
git remote add origin https://github.com/YOUR_USERNAME/app-2.0.git
git branch -M main
```

### Bước 3: Đẩy Lên GitHub
```powershell
git push -u origin main
```

Nếu yêu cầu authentication:
- **Dùng GitHub Personal Access Token (PAT)** thay vì password:
  1. Vào https://github.com/settings/tokens
  2. Chọn "Generate new token (classic)"
  3. Chọn scopes: `repo`
  4. Copy token làm password khi push

---

## 🔐 Kiểm Tra An Toàn Trước Khi Push

```powershell
# Kiểm tra tất cả đã sẵn sàng
git status  # Không được có .env

# Xem lại commit
git log --oneline

# Kiểm tra file sắp push
git show HEAD
```

---

## ⚠️ Nếu Vô Tình Commit .env (Khẩn Cấp)

```powershell
# Xóa file khỏi git (nhưng giữ local)
git rm --cached .env

# Commit lại
git commit -m "Remove .env file from tracking"

# Push
git push
```

**Cảnh báo**: Nếu .env đã được push:
- ⚠️ **Regenerate tất cả API keys ngay lập tức**
- Xóa repo, tạo mới, push lại

---

## 📌 Hướng Dẫn Cho Người Khác Clone

```markdown
## Setup Hướng Dẫn

1. Clone repository
   \`\`\`bash
   git clone https://github.com/YOUR_USERNAME/app-2.0.git
   cd app-2.0
   \`\`\`

2. Tạo file .env từ template
   \`\`\`bash
   cp .env.example .env
   \`\`\`

3. Cập nhật .env với keys thực
   \`\`\`
   OPENAI_API_KEY=sk-...
   TELEGRAM_BOT_TOKEN=...
   TAVILY_API_KEY=...
   QDRANT_API_KEY=...
   FACEBOOK_ACCESS_TOKEN=...
   FACEBOOK_PAGE_ID=...
   \`\`\`

4. Cài dependencies
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

5. Chạy ứng dụng
   \`\`\`bash
   python main.py
   \`\`\`
```

---

## ✅ Checklist Trước Push

- [ ] `.env` không trong staged files
- [ ] Không có hardcoded secrets trong code
- [ ] `.gitignore` đã được commit
- [ ] `.env.example` đã được commit
- [ ] README.md được cập nhật nếu cần
- [ ] Không có `__pycache__/` hoặc `*.db`
- [ ] Commit message rõ ràng

---

## 🔗 Tài Liệu Tham Khảo
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitIgnore Best Practices](https://github.com/github/gitignore)
- [Managing Sensitive Data](https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files)
