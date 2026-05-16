#!/usr/bin/env python3
"""
استخراج تمام آثار یک نویسنده از OpenITI و ذخیره به صورت JSON
استفاده: python build_author.py --name "شمس الدین ذهبی" --id "0748Dhahabi" --year 748 --output dhahabi.json
"""

import os
import sys
import json
import yaml
import argparse
import subprocess
from pathlib import Path


def clone_openiti_repo(death_year, target_dir="openiti_repo"):
    """
    مخزن OpenITI مربوط به قرن وفات نویسنده را کلون می‌کند.
    ساختار: سال ۷۴۸ → مخزن 0700AH
    """
    century = (death_year // 100) * 100
    repo_name = f"{century:04d}AH"
    repo_url = f"https://github.com/OpenITI/{repo_name}.git"
    
    print(f"📥 در حال کلون کردن مخزن {repo_name} ...")
    
    if not os.path.exists(target_dir):
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ خطا در کلون مخزن: {result.stderr}")
            sys.exit(1)
        print(f"✅ مخزن با موفقیت کلون شد.")
    else:
        print(f"✅ مخزن از قبل وجود دارد.")
    
    return target_dir


def find_author_folders(repo_dir, author_id):
    """
    پوشه‌های مربوط به یک نویسنده خاص را در دایرکتوری data پیدا می‌کند.
    نام پوشه‌ها با شناسه نویسنده شروع می‌شود (مثلاً '0748Dhahabi')
    """
    data_dir = os.path.join(repo_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"❌ دایرکتوری data یافت نشد: {data_dir}")
        return []
    
    author_folders = []
    for folder in sorted(os.listdir(data_dir)):
        if folder.startswith(author_id):
            author_folders.append(os.path.join(data_dir, folder))
    
    print(f"📚 {len(author_folders)} کتاب برای {author_id} یافت شد.")
    return author_folders


def parse_yaml_metadata(readme_path):
    """
    فراداده YAML را از فایل README.md استخراج می‌کند.
    فراداده بین دو خط '---' قرار دارد.
    """
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # استخراج بخش YAML
        if content.startswith('---'):
            parts = content.split('---')
            if len(parts) >= 3:
                yaml_content = parts[1]
                return yaml.safe_load(yaml_content)
        
        return {}
    except Exception as e:
        print(f"⚠️ خطا در خواندن فراداده {readme_path}: {e}")
        return {}


def extract_book_text(book_folder):
    """
    تمام فایل‌های متنی یک کتاب را می‌خواند و ادغام می‌کند.
    فایل‌ها با پسوندهای mARkdown، txt و md (به جز README.md) خوانده می‌شوند.
    """
    full_text_parts = []
    text_files = []
    
    # جمع‌آوری تمام فایل‌های متنی
    for root, _, files in os.walk(book_folder):
        for file in files:
            if file == 'README.md':
                continue
            if file.endswith(('.mARkdown', '.txt', '.md')):
                text_files.append(os.path.join(root, file))
    
    # مرتب‌سازی و خواندن فایل‌ها
    for file_path in sorted(text_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():  # فقط اگر محتوا خالی نباشد
                    full_text_parts.append(content)
        except UnicodeDecodeError:
            try:
                # تلاش با encoding جایگزین
                with open(file_path, 'r', encoding='utf-16') as f:
                    content = f.read()
                    if content.strip():
                        full_text_parts.append(content)
            except Exception as e:
                print(f"⚠️ خطا در خواندن {file_path}: {e}")
        except Exception as e:
            print(f"⚠️ خطا در خواندن {file_path}: {e}")
    
    return "\n\n".join(full_text_parts)


def build_author_json(author_name, author_id, death_year, output_file):
    """
    تابع اصلی: تمام آثار یک نویسنده را جمع‌آوری و در فایل JSON ذخیره می‌کند.
    """
    print(f"\n{'='*60}")
    print(f"🔄 شروع پردازش: {author_name}")
    print(f"   شناسه: {author_id}")
    print(f"   سال وفات: {death_year}")
    print(f"{'='*60}\n")
    
    # کلون مخزن
    repo_dir = clone_openiti_repo(death_year)
    
    # یافتن پوشه‌های نویسنده
    author_folders = find_author_folders(repo_dir, author_id)
    
    if not author_folders:
        print(f"❌ هیچ کتابی برای {author_name} یافت نشد.")
        # ایجاد فایل JSON خالی
        empty_data = {
            "author_name": author_name,
            "author_id": author_id,
            "death_year": death_year,
            "source": "OpenITI",
            "total_books": 0,
            "books": []
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, ensure_ascii=False, indent=2)
        return
    
    # پردازش هر کتاب
    all_books = []
    
    for i, folder in enumerate(author_folders, 1):
        folder_name = os.path.basename(folder)
        print(f"📖 [{i}/{len(author_folders)}] پردازش: {folder_name}")
        
        readme_path = os.path.join(folder, 'README.md')
        
        # استخراج فراداده
        metadata = {}
        if os.path.exists(readme_path):
            metadata = parse_yaml_metadata(readme_path)
        
        # استخراج عنوان کتاب
        book_title = folder_name
        if metadata:
            if 'title' in metadata:
                book_title = metadata['title']
            elif 'Title' in metadata:
                book_title = metadata['Title']
        
        # استخراج متن کتاب
        text = extract_book_text(folder)
        
        # ساخت آبجکت کتاب
        book_entry = {
            "folder_name": folder_name,
            "title": book_title,
            "metadata": metadata,
            "text_length": len(text),
            "text": text
        }
        
        all_books.append(book_entry)
        print(f"   ✅ عنوان: {book_title}")
        print(f"   📝 طول متن: {len(text):,} کاراکتر")
    
    # ساخت JSON نهایی
    author_data = {
        "author_name": author_name,
        "author_id": author_id,
        "death_year": death_year,
        "source": "OpenITI",
        "total_books": len(all_books),
        "books": all_books
    }
    
    # ذخیره در فایل
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(author_data, f, ensure_ascii=False, indent=2)
    
    # محاسبه حجم فایل
    file_size = os.path.getsize(output_file) / (1024 * 1024)  # به مگابایت
    
    print(f"\n{'='*60}")
    print(f"✅ پردازش با موفقیت به پایان رسید!")
    print(f"   📚 تعداد کتاب‌ها: {len(all_books)}")
    print(f"   💾 حجم فایل خروجی: {file_size:.2f} MB")
    print(f"   📄 فایل: {output_file}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='استخراج تمام آثار یک نویسنده از OpenITI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال استفاده:
  python build_author.py --name "شمس الدین ذهبی" --id "0748Dhahabi" --year 748 --output dhahabi.json
  python build_author.py -n "ابن قیم جوزیه" -i "0751IbnQayyim" -y 751 -o ibnqayyim.json
        """
    )
    
    parser.add_argument('-n', '--name', required=True, help='نام کامل نویسنده')
    parser.add_argument('-i', '--id', required=True, help='شناسه نویسنده در OpenITI (مثال: 0748Dhahabi)')
    parser.add_argument('-y', '--year', type=int, required=True, help='سال وفات نویسنده')
    parser.add_argument('-o', '--output', default='author_works.json', help='نام فایل خروجی (پیش‌فرض: author_works.json)')
    
    args = parser.parse_args()
    
    build_author_json(args.name, args.id, args.year, args.output)


if __name__ == "__main__":
    main()
