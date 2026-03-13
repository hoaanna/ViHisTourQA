import os
from transformers import pipeline
import torch
from tqdm import tqdm

# ==== Cấu hình ====
input_folder = "lich_su_txts"
output_folder = "corrected_txt"
# ==================

class AdvancedVietnameseCorrector:
    def __init__(self):
        print("[📦] Đang khởi tạo model AI...")
        
        # Thử các model theo thứ tự ưu tiên
        self.models_priority = [
            ("VietAI/vit5-base", "text2text-generation"),
            ("google/mt5-small", "text2text-generation"),
            ("vinai/phobert-base", "fill-mask"),
        ]
        
        self.corrector = None
        self.model_type = None
        
        for model_name, task in self.models_priority:
            try:
                print(f"[🔄] Đang thử {model_name}...")
                self.corrector = pipeline(
                    task,
                    model=model_name,
                    device=-1,  # CPU
                    torch_dtype=torch.float32
                )
                self.model_name = model_name
                self.model_type = task
                print(f"[✅] Thành công với {model_name}")
                break
            except Exception as e:
                print(f"[⚠️] Lỗi {model_name}: {e}")
                continue
        
        if not self.corrector:
            print("[❌] Không thể tải model AI, sử dụng phương pháp cơ bản")
            self.use_basic_correction = True
        else:
            self.use_basic_correction = False
    
    def correct_with_ai(self, text):
        """Sửa bằng AI model"""
        if self.use_basic_correction:
            return self.basic_correct(text)
        
        try:
            if self.model_type == "text2text-generation":
                if "vit5" in self.model_name.lower():
                    prompt = f"Sửa lỗi chính tả: {text}"
                else:
                    prompt = f"correct grammar: {text}"
                
                result = self.corrector(
                    prompt,
                    max_length=min(len(text) + 100, 512),
                    num_beams=2,
                    early_stopping=True,
                    do_sample=False
                )
                
                corrected = result[0]['generated_text']
                
                # Làm sạch
                prefixes = ["Sửa lỗi chính tả:", "correct grammar:", "grammar:"]
                for prefix in prefixes:
                    if corrected.startswith(prefix):
                        corrected = corrected.replace(prefix, "").strip()
                
                return corrected
            
            elif self.model_type == "fill-mask":
                # Xử lý với PhoBERT (phức tạp hơn)
                return self.correct_with_phobert(text)
            
        except Exception as e:
            print(f"[⚠️] Lỗi AI correction: {e}")
            return self.basic_correct(text)
    
    def basic_correct(self, text):
        """Phương pháp sửa cơ bản"""
        corrections = {
            "k": "không", "ko": "không", "dc": "được", "đc": "được",
            "vs": "với", "mik": "mình", "bn": "bạn", "tui": "tôi",
            "bik": "biết", "hok": "không", "wa": "quá", "dz": "vậy"
        }
        
        import re
        for wrong, correct in corrections.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        return text
    
    def correct_text(self, text):
        """Sửa text (AI + basic)"""
        if len(text.strip()) == 0:
            return text
        
        # Chia nhỏ nếu quá dài
        if len(text) > 300:
            sentences = text.split('.')
            corrected_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    corrected = self.correct_with_ai(sentence.strip())
                    corrected_sentences.append(corrected)
            
            return '. '.join(corrected_sentences)
        else:
            return self.correct_with_ai(text)

def main():
    corrector = AdvancedVietnameseCorrector()
    
    # Tạo thư mục đầu ra
    os.makedirs(output_folder, exist_ok=True)
    
    # Lấy danh sách files
    txt_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]
    
    if not txt_files:
        print(f"[❌] Không tìm thấy file .txt nào trong {input_folder}")
        return
    
    print(f"[📁] Tìm thấy {len(txt_files)} files")
    
    # Xử lý từng file
    for file_name in tqdm(txt_files, desc="Đang sửa với AI"):
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, f"ai_corrected_{file_name}")
        
        try:
            # Đọc file
            with open(input_path, "r", encoding="utf-8", errors='ignore') as f:
                original_text = f.read()
            
            # Sửa bằng AI
            corrected_text = corrector.correct_text(original_text)
            
            # Lưu kết quả
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(corrected_text)
            
        except Exception as e:
            print(f"[❌] Lỗi xử lý {file_name}: {e}")
            continue
    
    print(f"\n[🎉] Hoàn thành! Kết quả trong: {output_folder}")

if __name__ == "__main__":
    main()
