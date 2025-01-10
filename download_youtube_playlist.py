import yt_dlp
import pandas as pd
from datetime import datetime
import os
from typing import Dict, List, Optional
import logging

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_downloader.log'),
        logging.StreamHandler()
    ]
)

def setup_download_folder(folder: str) -> None:
    """
    Membuat dan memvalidasi folder download
    """
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
            logging.info(f"Folder {folder} berhasil dibuat")
        except Exception as e:
            logging.error(f"Gagal membuat folder {folder}: {e}")
            raise

def get_video_info(url: str, is_playlist_item: bool = False) -> Dict:
    """
    Mengambil informasi video dengan penanganan error yang lebih baik
    """
    try:
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
            'extract_flat': True if is_playlist_item else False,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            return {
                'judul': info_dict.get('title', 'Tidak tersedia'),
                'url': url,
                'durasi_detik': info_dict.get('duration', 0),
                'durasi_menit': round(info_dict.get('duration', 0) / 60, 2) if info_dict.get('duration') else 0,
                'channel': info_dict.get('uploader', 'Tidak tersedia'),
                'jumlah_views': info_dict.get('view_count', 0),
                'tanggal_publikasi': datetime.strptime(info_dict.get('upload_date', '19700101'), '%Y%m%d').strftime('%Y-%m-%d') if info_dict.get('upload_date') else 'Tidak tersedia',
                'deskripsi': info_dict.get('description', 'Tidak tersedia')
            }
    except Exception as e:
        logging.error(f"Gagal mengambil info untuk {url}: {str(e)}")
        return {
            'judul': 'Tidak tersedia',
            'url': url,
            'durasi_detik': 0,
            'durasi_menit': 0,
            'channel': 'Tidak tersedia',
            'jumlah_views': 0,
            'tanggal_publikasi': 'Tidak tersedia',
            'deskripsi': 'Tidak tersedia'
        }

def download_video(url: str, download_folder: str) -> bool:
    """
    Mendownload video dengan penanganan error dan progress callback
    """
    def progress_hook(d):
        if d['status'] == 'downloading':
            progress = d.get('_percent_str', '0%')
            logging.info(f"Downloading: {progress}")
        elif d['status'] == 'finished':
            logging.info(f"Download selesai: {d['filename']}")

    try:
        ydl_opts = {
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
            'format': 'best',
            'progress_hooks': [progress_hook],
            'ignoreerrors': True,
            'no_warnings': True,
            'quiet': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        logging.error(f"Error saat mendownload {url}: {str(e)}")
        return False

def download_single_video(url: str, download_folder: str) -> Optional[Dict]:
    """
    Mendownload single video YouTube dan menyimpan informasinya
    """
    try:
        setup_download_folder(download_folder)
        logging.info(f"Memproses video: {url}")
        
        video_info = get_video_info(url)
        if download_video(url, download_folder):
            logging.info("Video berhasil didownload")
            
            # Menyimpan informasi ke file
            df = pd.DataFrame([video_info])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            csv_filename = f'youtube_video_{timestamp}.csv'
            excel_filename = f'youtube_video_{timestamp}.xlsx'
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            df.to_excel(excel_filename, index=False)
            
            logging.info(f"\nInformasi video telah disimpan ke:")
            logging.info(f"- CSV: '{csv_filename}'")
            logging.info(f"- Excel: '{excel_filename}'")
            
            return video_info
        else:
            logging.error("Gagal mendownload video")
            return None
            
    except Exception as e:
        logging.error(f"Error saat memproses video: {str(e)}")
        return None

def extract_playlist_info(playlist_url: str, download_folder: str = "downloaded_videos") -> Optional[List[Dict]]:
    """
    Mengekstrak informasi playlist YouTube dan mendownload video dengan progress tracking
    """
    try:
        setup_download_folder(download_folder)
        
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
            'extract_flat': True,
            'no_warnings': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
        
        if not playlist_info:
            logging.error("Gagal mendapatkan informasi playlist")
            return None
            
        logging.info(f"Mengekstrak playlist: {playlist_info['title']}")
        
        video_data = []
        failed_downloads = []
        total_videos = len(playlist_info['entries'])
        
        for index, video in enumerate(playlist_info['entries'], 1):
            try:
                video_url = video['url']
                logging.info(f"\nMemproses video {index}/{total_videos}")
                
                video_info = get_video_info(video_url, is_playlist_item=True)
                video_info['playlist'] = playlist_info['title']
                video_info['urutan_playlist'] = index
                video_data.append(video_info)
                
                if not download_video(video_url, download_folder):
                    failed_downloads.append(video_url)
                    
            except Exception as e:
                logging.error(f"Error pada video {index}: {str(e)}")
                failed_downloads.append(video_url)
                continue
        
        # Menyimpan data ke file
        if video_data:
            df = pd.DataFrame(video_data)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            csv_filename = f'youtube_playlist_{timestamp}.csv'
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            excel_filename = f'youtube_playlist_{timestamp}.xlsx'
            df.to_excel(excel_filename, index=False)
            
            logging.info(f"\nRingkasan:")
            logging.info(f"Total video dalam playlist: {total_videos}")
            logging.info(f"Video berhasil didownload: {total_videos - len(failed_downloads)}")
            logging.info(f"Video gagal didownload: {len(failed_downloads)}")
            
            if failed_downloads:
                logging.warning("\nDaftar video yang gagal didownload:")
                for url in failed_downloads:
                    logging.warning(url)
            
            logging.info(f"\nData telah disimpan ke:")
            logging.info(f"- CSV: '{csv_filename}'")
            logging.info(f"- Excel: '{excel_filename}'")
            
        return video_data
        
    except Exception as e:
        logging.error(f"Error utama: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        # Mengecek dan menginstall dependensi yang diperlukan
        required_packages = ['openpyxl', 'pandas', 'yt-dlp']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                logging.info(f"Menginstall {package}...")
                import subprocess
                subprocess.check_call(['pip', 'install', package])
        
        # Meminta input mode download
        print("\nPilih mode download:")
        print("1. Download single video")
        print("2. Download playlist")
        
        while True:
            mode = input("Masukkan pilihan (1/2): ").strip()
            if mode in ['1', '2']:
                break
            print("Pilihan tidak valid. Silakan pilih 1 atau 2.")
        
        # Meminta input URL dan folder
        url = input("Masukkan URL YouTube: ").strip()
        download_folder = input("Masukkan folder untuk menyimpan video (default: downloaded_videos): ").strip() or "downloaded_videos"
        
        # Proses sesuai mode yang dipilih
        if mode == '1':
            result = download_single_video(url, download_folder)
            if result is None:
                logging.error("Gagal memproses video")
        else:
            result = extract_playlist_info(url, download_folder)
            if result is None:
                logging.error("Gagal memproses playlist")
            
    except KeyboardInterrupt:
        logging.warning("\nProses dihentikan oleh pengguna")
    except Exception as e:
        logging.error(f"Error yang tidak terduga: {str(e)}")
# import yt_dlp
# import pandas as pd
# from datetime import datetime
# import os
# from typing import Dict, List, Optional
# import logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('youtube_downloader.log'),
#         logging.StreamHandler()
#     ]
# )

# def setup_download_folder(folder: str) -> None:
#     """
#     Membuat dan memvalidasi folder download
#     """
#     if not os.path.exists(folder):
#         try:
#             os.makedirs(folder)
#             logging.info(f"Folder {folder} berhasil dibuat")
#         except Exception as e:
#             logging.error(f"Gagal membuat folder {folder}: {e}")
#             raise

# def get_video_info(url: str) -> Dict:
#     """
#     Mengambil informasi video dengan penanganan error yang lebih baik
#     """
#     try:
#         ydl_opts = {
#             'quiet': True,
#             'force_generic_extractor': True,
#             'extract_flat': True,  # Ekstrak metadata saja tanpa download
#             'no_warnings': True
#         }
        
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info_dict = ydl.extract_info(url, download=False)
#             return {
#                 'judul': info_dict.get('title', 'Tidak tersedia'),
#                 'url': url,
#                 'durasi_detik': info_dict.get('duration', 0),
#                 'durasi_menit': round(info_dict.get('duration', 0) / 60, 2) if info_dict.get('duration') else 0,
#                 'channel': info_dict.get('uploader', 'Tidak tersedia'),
#                 'jumlah_views': info_dict.get('view_count', 0),
#                 'tanggal_publikasi': datetime.strptime(info_dict.get('upload_date', '19700101'), '%Y%m%d').strftime('%Y-%m-%d') if info_dict.get('upload_date') else 'Tidak tersedia',
#                 'deskripsi': info_dict.get('description', 'Tidak tersedia')
#             }
#     except Exception as e:
#         logging.error(f"Gagal mengambil info untuk {url}: {str(e)}")
#         return {
#             'judul': 'Tidak tersedia',
#             'url': url,
#             'durasi_detik': 0,
#             'durasi_menit': 0,
#             'channel': 'Tidak tersedia',
#             'jumlah_views': 0,
#             'tanggal_publikasi': 'Tidak tersedia',
#             'deskripsi': 'Tidak tersedia'
#         }

# def download_video(url: str, download_folder: str) -> bool:
#     """
#     Mendownload video dengan penanganan error dan progress callback
#     """
#     def progress_hook(d):
#         if d['status'] == 'downloading':
#             progress = d.get('_percent_str', '0%')
#             logging.info(f"Downloading: {progress}")
#         elif d['status'] == 'finished':
#             logging.info(f"Download selesai: {d['filename']}")

#     try:
#         ydl_opts = {
#             'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
#             'format': 'best',  # Atau 'bestvideo+bestaudio/best' untuk kualitas terbaik
#             'progress_hooks': [progress_hook],
#             'ignoreerrors': True,
#             'no_warnings': True,
#             'quiet': False
#         }
        
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#         return True
#     except Exception as e:
#         logging.error(f"Error saat mendownload {url}: {str(e)}")
#         return False

# def extract_playlist_info(playlist_url: str, download_folder: str = "downloaded_videos") -> Optional[List[Dict]]:
#     """
#     Mengekstrak informasi playlist YouTube dan mendownload video dengan progress tracking
#     """
#     try:
#         setup_download_folder(download_folder)
        
#         ydl_opts = {
#             'quiet': True,
#             'force_generic_extractor': True,
#             'extract_flat': True,
#             'no_warnings': True
#         }

#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             playlist_info = ydl.extract_info(playlist_url, download=False)
        
#         if not playlist_info:
#             logging.error("Gagal mendapatkan informasi playlist")
#             return None
            
#         logging.info(f"Mengekstrak playlist: {playlist_info['title']}")
        
#         video_data = []
#         failed_downloads = []
#         total_videos = len(playlist_info['entries'])
        
#         for index, video in enumerate(playlist_info['entries'], 1):
#             try:
#                 video_url = video['url']
#                 logging.info(f"\nMemproses video {index}/{total_videos}")
                
#                 video_info = get_video_info(video_url)
#                 video_info['playlist'] = playlist_info['title']
#                 video_info['urutan_playlist'] = index
#                 video_data.append(video_info)
                
#                 if not download_video(video_url, download_folder):
#                     failed_downloads.append(video_url)
                    
#             except Exception as e:
#                 logging.error(f"Error pada video {index}: {str(e)}")
#                 failed_downloads.append(video_url)
#                 continue
        
#         # Menyimpan data ke file
#         if video_data:
#             df = pd.DataFrame(video_data)
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
#             # Menyimpan ke CSV
#             csv_filename = f'youtube_playlist_{timestamp}.csv'
#             df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
#             # Menyimpan ke Excel
#             excel_filename = f'youtube_playlist_{timestamp}.xlsx'
#             df.to_excel(excel_filename, index=False)
            
#             logging.info(f"\nRingkasan:")
#             logging.info(f"Total video dalam playlist: {total_videos}")
#             logging.info(f"Video berhasil didownload: {total_videos - len(failed_downloads)}")
#             logging.info(f"Video gagal didownload: {len(failed_downloads)}")
            
#             if failed_downloads:
#                 logging.warning("\nDaftar video yang gagal didownload:")
#                 for url in failed_downloads:
#                     logging.warning(url)
            
#             logging.info(f"\nData telah disimpan ke:")
#             logging.info(f"- CSV: '{csv_filename}'")
#             logging.info(f"- Excel: '{excel_filename}'")
            
#         return video_data
        
#     except Exception as e:
#         logging.error(f"Error utama: {str(e)}")
#         return None

# if __name__ == "__main__":
#     try:
#         # Mengecek dan menginstall dependensi yang diperlukan
#         required_packages = ['openpyxl', 'pandas', 'yt-dlp']
#         for package in required_packages:
#             try:
#                 __import__(package)
#             except ImportError:
#                 logging.info(f"Menginstall {package}...")
#                 import subprocess
#                 subprocess.check_call(['pip', 'install', package])
        
#         playlist_url = input("Masukkan URL playlist YouTube: ")
#         download_folder = input("Masukkan folder untuk menyimpan video (default: downloaded_videos): ").strip() or "downloaded_videos"
        
#         video_data = extract_playlist_info(playlist_url, download_folder=download_folder)
        
#         if video_data is None:
#             logging.error("Gagal memproses playlist")
            
#     except KeyboardInterrupt:
#         logging.warning("\nProses dihentikan oleh pengguna")
#     except Exception as e:
#         logging.error(f"Error yang tidak terduga: {str(e)}")
