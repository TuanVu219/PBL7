import time
import subprocess
import schedule
from django.core.management.base import BaseCommand
from datetime import datetime

class Command(BaseCommand):
    help = 'Kích hoạt đồng hồ canh giờ chạy NLP phân tích từ khóa tự động vào 23:00 mỗi đêm'

    def run_nlp_job(self):
        self.stdout.write(self.style.WARNING(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🧠 ĐANG KÍCH HOẠT NLP ENGINE..."))
        try:
            # 🟢 SỬA TÊN FILE: Đổi 'ten_file_nlp_cua_ban.py' thành tên file code chạy NLP thực tế của bạn
            subprocess.run(
                ["python", "nlp_engine.py"], 
                check=True, shell=True
            )
            self.stdout.write(self.style.SUCCESS("✅ NLP PHÂN TÍCH TỪ KHÓA THÀNH CÔNG!"))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"🚨 LỖI KHI CHẠY NLP: {e}"))

    def daily_nlp(self):
        self.stdout.write(self.style.SUCCESS(f"\n======================================================="))
        self.stdout.write(self.style.SUCCESS(f"🚀 BẮT ĐẦU TIẾN TRÌNH PHÂN TÍCH NGÀY {datetime.now().strftime('%Y-%m-%d')}"))
        
        # Chỉ gọi hàm chạy NLP
        self.run_nlp_job()
            
        self.stdout.write(self.style.SUCCESS(f"🏁 KẾT THÚC TIẾN TRÌNH NGÀY {datetime.now().strftime('%Y-%m-%d')}"))
        self.stdout.write(self.style.SUCCESS(f"=======================================================\n"))
        self.stdout.write(self.style.WARNING("⏳ Hệ thống tiếp tục ngủ đông và chờ đến 23:00 ngày mai..."))

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 ĐỒNG HỒ AUTO NLP ĐÃ ĐƯỢC BẬT!"))
        self.stdout.write(self.style.WARNING("⏰ Lịch trình: 23:00 mỗi ngày."))
        self.stdout.write("⚠️  Lưu ý: Giữ Terminal này luôn mở để hệ thống canh giờ.\n")

        # Cài đặt giờ G (23:00 = 11h đêm)
        schedule.every().day.at("23:00").do(self.daily_nlp)

        # Vòng lặp vô hạn để canh đồng hồ
        while True:
            schedule.run_pending()
            time.sleep(30) # Kiểm tra đồng hồ mỗi 30s để không làm nặng CPU