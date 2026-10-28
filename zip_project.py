import os
import zipfile

def zip_project(source_dir, output_filename):
    # Folder dan file yang TIDAK BOLEH ikut di-ZIP karena memberatkan
    exclude_dirs = {'node_modules', 'venv', '__pycache__', '.git', '.gemini', '.pytest_cache'}
    exclude_exts = {'.zip', '.pyc'}

    print(f"Memulai proses ZIP ke {output_filename}...")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Hapus folder yang ada di daftar exclude agar tidak dikunjungi (modifikasi list in-place)
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Lewati file dengan ekstensi tertentu atau file zip itu sendiri
                if any(file.endswith(ext) for ext in exclude_exts) or file == output_filename:
                    continue
                
                file_path = os.path.join(root, file)
                # Buat path relatif di dalam ZIP
                arcname = os.path.relpath(file_path, source_dir)
                
                # Tambahkan file ke dalam zip
                zipf.write(file_path, arcname)
                print(f"Menambahkan: {arcname}")
                
    print(f"\n[SUKSES] Berhasil membungkus project ke: {output_filename}")
    print("Silakan upload file zip ini ke VPS Hostinger Anda.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    zip_project(current_dir, "metrik-app.zip")
