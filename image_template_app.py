import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QLineEdit, QFrame, QSizePolicy,
                            QSlider, QFormLayout)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPainterPath, QColor, QFont
from PyQt5.QtCore import Qt, QRect, QSize, QRectF
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import numpy as np

class ImageTemplateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Muzikos Viršelio Kūrėjas")
        self.setMinimumSize(800, 600)
        
        self.input_image_path = None
        self.processed_image = None
        self.blur_amount = 60  # Numatytasis blur kiekis (60%)
        
        self.init_ui()
    
    def init_ui(self):
        # Pagrindinis išdėstymas
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Kairysis skydelis - įvesties kontrolės
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # Vaizdo pasirinkimo mygtukas
        self.select_image_btn = QPushButton("Pasirinkti vaizdą")
        self.select_image_btn.clicked.connect(self.select_image)
        left_layout.addWidget(self.select_image_btn)
        
        # Formos išdėstymas
        form_layout = QFormLayout()
        
        # Pavadinimo įvestis
        self.title_input = QLineEdit()
        self.title_input.textChanged.connect(self.on_text_changed)
        form_layout.addRow("Pavadinimas:", self.title_input)
        
        # Atlikėjo įvestis
        self.artist_input = QLineEdit()
        self.artist_input.textChanged.connect(self.on_text_changed)
        form_layout.addRow("Atlikėjas:", self.artist_input)
        
        # Blur slankiklis
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(100)
        self.blur_slider.setValue(self.blur_amount)
        self.blur_slider.setTickPosition(QSlider.TicksBelow)
        self.blur_slider.setTickInterval(10)
        self.blur_slider.valueChanged.connect(self.on_blur_changed)
        form_layout.addRow("Blur efektas:", self.blur_slider)
        
        # Blur vertės etiketė
        self.blur_value_label = QLabel(f"{self.blur_amount}%")
        form_layout.addRow("", self.blur_value_label)
        
        left_layout.addLayout(form_layout)
        
        # Eksporto mygtukas
        self.export_btn = QPushButton("Eksportuoti")
        self.export_btn.clicked.connect(self.export_image)
        self.export_btn.setEnabled(False)
        left_layout.addWidget(self.export_btn)
        
        left_layout.addStretch()
        
        # Dešinysis skydelis - peržiūra
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Peržiūros etiketė
        self.preview_label = QLabel("Peržiūra")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(450, 800)  # 9:16 santykis
        self.preview_label.setStyleSheet("background-color: #222; color: white;")
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.preview_label)
        
        # Pridėti skydelius į pagrindinį išdėstymą
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)  # Dešinysis skydelis užima daugiau vietos
    
    def on_text_changed(self):
        """Atnaujina peržiūrą, kai keičiasi tekstas"""
        if self.input_image_path:
            self.process_image()
    
    def on_blur_changed(self, value):
        """Atnaujina blur efektą ir peržiūrą"""
        self.blur_amount = value
        self.blur_value_label.setText(f"{value}%")
        if self.input_image_path:
            self.process_image()
    
    def select_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Pasirinkti vaizdą", "", "Vaizdų failai (*.png *.jpg *.jpeg)")
        
        if file_path:
            self.input_image_path = file_path
            self.process_image()
            self.export_btn.setEnabled(True)
    
    def process_image(self):
        if not self.input_image_path:
            return
        
        # Atnaujinti peržiūrą pagal įvesties laukus
        title = self.title_input.text() or "TAU MICH AUF"
        artist = self.artist_input.text() or "NIKLAS DEE"
        
        # Apdoroti vaizdą
        self.processed_image = self.create_template(self.input_image_path, title, artist)
        
        # Konvertuoti PIL vaizdą į QPixmap
        img_array = np.array(self.processed_image)
        height, width, channels = img_array.shape
        bytes_per_line = channels * width
        q_img = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # Pritaikyti peržiūros etiketei
        scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)
    
    def create_template(self, image_path, title, artist):
        # Atidaryti pradinį vaizdą
        original = Image.open(image_path).convert("RGB")
        
        # Sukurti 9:16 santykio drobę
        target_width = 1080  # Standartinis 9:16 plotis
        target_height = 1920  # Standartinis 9:16 aukštis
        
        # Pritaikyti vaizdą 9:16 santykiui
        width, height = original.size
        target_ratio = 9/16
        
        # Nustatyti naują dydį išlaikant santykį
        if width / height > target_ratio:  # Per platus
            new_width = int(height * target_ratio)
            new_height = height
            original_resized = original.crop(((width - new_width) // 2, 0, (width + new_width) // 2, height))
        else:  # Per aukštas
            new_width = width
            new_height = int(width / target_ratio)
            original_resized = original.crop((0, (height - new_height) // 2, width, (height + new_height) // 2))
        
        # Pakeisti dydį
        background = original_resized.resize((target_width, target_height), Image.LANCZOS)
        
        # Pritaikyti blur efektą
        if self.blur_amount > 0:
            blur_radius = self.blur_amount / 10
            background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Sukurti tamsinimo sluoksnį
        overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 100))
        
        # Sukurti galutinį vaizdą
        final_image = Image.new("RGB", (target_width, target_height))
        final_image.paste(background, (0, 0))
        
        # Pritaikyti tamsinimo sluoksnį
        temp = Image.new("RGBA", (target_width, target_height))
        temp.paste(final_image.convert("RGBA"), (0, 0))
        final_image = Image.alpha_composite(temp, overlay).convert("RGB")
        
        # Sukurti centrinį kvadratinį vaizdą
        # Apkarpyti originalią nuotrauką iki kvadrato (1:1 santykio)
        square_img = self.crop_to_square(original)
        
        # Nustatyti kvadrato dydį (~70% ekrano pločio)
        square_size = int(target_width * 0.7)
        padding = 10  # 10px padding aplink kvadratą
        
        # Pakeisti dydį
        square_img = square_img.resize((square_size, square_size), Image.LANCZOS)
        
        # Sukurti apvalintų kampų kaukę
        mask = Image.new('L', (square_size, square_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        corner_radius = 40
        draw_mask.rounded_rectangle([(0, 0), (square_size, square_size)], corner_radius, fill=255)
        
        # Centruoti poziciją
        x_pos = (target_width - square_size) // 2
        y_pos = int(target_height * 0.3)  # Maždaug 30% nuo viršaus
        
        # Sukurti patamsintą foną kvadratui (75% ryškumo)
        dark_bg = Image.new('RGBA', (square_size + padding*2, square_size + padding*2), (0, 0, 0, 64))
        dark_bg_mask = Image.new('L', (square_size + padding*2, square_size + padding*2), 0)
        dark_bg_draw = ImageDraw.Draw(dark_bg_mask)
        dark_bg_draw.rounded_rectangle([(0, 0), (square_size + padding*2, square_size + padding*2)], 
                                      corner_radius + padding, fill=255)
        dark_bg.putalpha(dark_bg_mask)
        
        # Įklijuoti patamsintą foną
        x_bg = x_pos - padding
        y_bg = y_pos - padding
        final_image.paste(dark_bg.convert('RGB'), (x_bg, y_bg), dark_bg_mask)
        
        # Įklijuoti kvadratinį vaizdą su apvalintais kampais
        final_image.paste(square_img, (x_pos, y_pos), mask)
        
        # Pridėti teksto elementus
        draw = ImageDraw.Draw(final_image)
        
        # Atlikėjo vardas - didžiosiomis raidėmis
        artist_y = int(target_height * 0.75)  # 75% nuo viršaus
        artist_x = target_width // 2  # Centruota
        self.draw_text_centered(draw, artist.upper(), artist_x, artist_y, 60)
        
        # Dainos pavadinimas - po atlikėjo vardu
        title_y = artist_y + 80
        title_x = target_width // 2  # Centruota
        self.draw_text_centered(draw, title, title_x, title_y, 45)
        
        # Progreso juosta - balta linija su tašku
        progress_y = title_y + 100
        self.draw_progress_bar(draw, target_width, progress_y)
        
        # Medijos valdikliai
        controls_y = progress_y + 80
        self.draw_media_controls(draw, target_width, controls_y)
        
        return final_image
    
    def crop_to_square(self, image):
        """Apkarpo vaizdą iki kvadrato (1:1 santykio)"""
        width, height = image.size
        if width > height:
            left = (width - height) // 2
            right = left + height
            top = 0
            bottom = height
        else:
            top = (height - width) // 2
            bottom = top + width
            left = 0
            right = width
        
        return image.crop((left, top, right, bottom))
    
    def draw_text_centered(self, draw, text, x, y, font_size):
        """Piešia tekstą centruotą horizontaliai"""
        font = self.get_font(font_size)
        
        # Gauti teksto dydį
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            text_width, text_height = draw.textsize(text, font=font)
        
        # Apskaičiuojame centravimo pozicijas
        text_x = x - text_width // 2
        text_y = y - text_height // 2
        
        # Pagrindinis tekstas
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
    def get_font(self, size):
        """Gauna šriftą"""
        font_options = [
            "GOTHICB.TTF", "GOTH.TTF", "arial.ttf", "arialbd.ttf", 
            "GOTHIC.TTF", "impact.ttf", "IMPACT.TTF"
        ]
        
        font_dirs = [
            "",  # Dabartinis katalogas
            "C:/Windows/Fonts/",  # Windows šriftai
            "/usr/share/fonts/",  # Linux šriftai
            "/System/Library/Fonts/"  # Mac šriftai
        ]
        
        # Bandome rasti šriftą
        for font_name in font_options:
            for font_dir in font_dirs:
                try:
                    font_path = os.path.join(font_dir, font_name)
                    return ImageFont.truetype(font_path, size)
                except (IOError, OSError):
                    continue
        
        return ImageFont.load_default()
    
    def draw_progress_bar(self, draw, width, y_pos):
        # Progreso juosta - balta linija
        bar_width = int(width * 0.7)  # 70% ekrano pločio
        bar_height = 2
        bar_x = (width - bar_width) // 2
        
        # Balta juosta
        draw.rectangle([(bar_x, y_pos), (bar_x + bar_width, y_pos + bar_height)], 
                      fill=(255, 255, 255))
        
        # Progreso taškas - baltas apskritimas
        progress_pos = bar_x + int(bar_width * 0.25)  # Maždaug 25% nuo kairės
        circle_radius = 8
        draw.ellipse([(progress_pos - circle_radius, y_pos - circle_radius + bar_height//2), 
                     (progress_pos + circle_radius, y_pos + circle_radius + bar_height//2)], 
                    fill=(255, 255, 255))
    
    def draw_media_controls(self, draw, width, y_pos):
        # Medijos valdikliai - ankstesnis, atkurti/pristabdyti, kitas
        center_x = width // 2
        button_spacing = width // 6
        
        # Ankstesnis mygtukas (kairėje) - dvigubas trikampis
        prev_x = center_x - button_spacing
        prev_size = 25
        
        # Pirmas trikampis
        draw.polygon([
            (prev_x - prev_size//2, y_pos),
            (prev_x + prev_size//2, y_pos - prev_size),
            (prev_x + prev_size//2, y_pos + prev_size)
        ], fill=(255, 255, 255))
        
        # Atkurti/Pristabdyti mygtukas (centre) - apskritimas su dviem linijomis
        play_x = center_x
        play_size = 40
        
        # Apskritimas
        draw.ellipse([
            (play_x - play_size, y_pos - play_size),
            (play_x + play_size, y_pos + play_size)
        ], outline=(255, 255, 255), width=3)
        
        # Dvi vertikalios linijos (pauzės simbolis)
        line_width = 6
        line_height = play_size
        spacing = 8
        
        draw.rectangle([
            (play_x - spacing - line_width//2, y_pos - line_height//2),
            (play_x - spacing + line_width//2, y_pos + line_height//2)
        ], fill=(255, 255, 255))
        
        draw.rectangle([
            (play_x + spacing - line_width//2, y_pos - line_height//2),
            (play_x + spacing + line_width//2, y_pos + line_height//2)
        ], fill=(255, 255, 255))
        
        # Kitas mygtukas (dešinėje) - dvigubas trikampis
        next_x = center_x + button_spacing
        next_size = 25
        
        # Pirmas trikampis
        draw.polygon([
            (next_x + next_size//2, y_pos),
            (next_x - next_size//2, y_pos - next_size),
            (next_x - next_size//2, y_pos + next_size)
        ], fill=(255, 255, 255))
    
    def export_image(self):
        if not self.processed_image:
            return
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Išsaugoti vaizdą", "", "PNG failai (*.png);;JPEG failai (*.jpg)")
        
        if file_path:
            self.processed_image.save(file_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTemplateApp()
    window.show()
    sys.exit(app.exec_()) 