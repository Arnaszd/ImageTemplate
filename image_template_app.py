import sys
import os
import random
import time
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QLineEdit, QFrame, QSizePolicy,
                            QSlider, QFormLayout, QMessageBox, QDialog, QTextEdit, 
                            QComboBox, QProgressDialog, QCheckBox)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPainterPath, QColor, QFont, QCursor, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QSize, QRectF, QTimer, QPoint, pyqtSignal, QObject, QThread
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import tempfile
import keyring
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass
import json
from email.header import Header

# Kurkime signalų klasę, kuri leis komunikuoti tarp gijų
class WorkerSignals(QObject):
    finished = pyqtSignal(object)

# Darbinė gija vaizdo apdorojimui
class ImageProcessingThread(Thread):
    def __init__(self, app, image_path, title, artist, blur_amount):
        Thread.__init__(self)
        self.app = app
        self.image_path = image_path
        self.title = title
        self.artist = artist
        self.blur_amount = blur_amount
        self.signals = WorkerSignals()
        
    def run(self):
        # Apdoroti vaizdą atskiroje gijoje
        result = self.app.create_template(self.image_path, self.title, self.artist, self.blur_amount)
        self.signals.finished.emit(result)

# Pagrindinis žvaigždžių animacijos klasė
class StarryBackground(QWidget):
    def __init__(self, star_count=100, parent=None):
        super(StarryBackground, self).__init__(parent)
        self.setAutoFillBackground(True)
        
        # Nustatyti juodą foną
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(10, 10, 20))  # Tamsiai mėlynas-juodas fonas
        self.setPalette(palette)
        
        # Žvaigždžių parametrai
        self.star_count = star_count
        self.stars = []
        self.generate_stars()
        
        # Animacijos laikmatis
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stars)
        self.timer.start(50)  # Atnaujinti kas 50ms
    
    def generate_stars(self):
        # Sugeneruoti atsitiktines žvaigždes
        for _ in range(self.star_count):
            x = random.randint(0, self.width() or 800)
            y = random.randint(0, self.height() or 600)
            size = random.uniform(1, 3)
            brightness = random.uniform(0.3, 1.0)
            twinkle_speed = random.uniform(0.01, 0.05)
            twinkle_direction = random.choice([-1, 1])
            
            self.stars.append({
                'x': x,
                'y': y,
                'size': size,
                'brightness': brightness,
                'twinkle_speed': twinkle_speed,
                'twinkle_direction': twinkle_direction
            })
    
    def update_stars(self):
        # Atnaujinti žvaigždžių mirgėjimą
        for star in self.stars:
            # Keisti ryškumą
            star['brightness'] += star['twinkle_speed'] * star['twinkle_direction']
            
            # Jei pasiekiama riba, pakeisti kryptį
            if star['brightness'] > 1.0:
                star['brightness'] = 1.0
                star['twinkle_direction'] = -1
            elif star['brightness'] < 0.3:
                star['brightness'] = 0.3
                star['twinkle_direction'] = 1
        
        # Atnaujinti ekraną
        self.update()
    
    def resizeEvent(self, event):
        # Perkurti žvaigždes, kai keičiasi lango dydis
        self.stars = []
        self.generate_stars()
        super(StarryBackground, self).resizeEvent(event)
    
    def paintEvent(self, event):
        # Nupiešti žvaigždes
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for star in self.stars:
            color = QColor(255, 255, 255, int(255 * star['brightness']))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            
            # Nupiešti žvaigždę kaip apskritimą
            painter.drawEllipse(
                QRectF(
                    star['x'] - star['size'] / 2,
                    star['y'] - star['size'] / 2,
                    star['size'],
                    star['size']
                )
            )

class EmailDialog(QDialog):
    """Dialogo langas el. pašto informacijai įvesti"""
    def __init__(self, parent=None, saved_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Siųsti el. paštu")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: white;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #3D3D3D;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#cancelBtn {
                background-color: #f44336;
            }
            QPushButton#cancelBtn:hover {
                background-color: #d32f2f;
            }
        """)
        
        # Dialogo išdėstymas
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # El. pašto formos išdėstymas
        form_layout = QFormLayout()
        
        # Gavėjo el. paštas - su numatytuoju adresu
        self.to_email = QLineEdit()
        if saved_settings and saved_settings.get('to_email'):
            self.to_email.setText(saved_settings.get('to_email'))
        else:
            # Numatytasis gavėjo adresas
            self.to_email.setText("tommaner1999@gmail.com")
            
        form_layout.addRow("Gavėjo el. paštas:", self.to_email)
        
        # Prisiminti mane žymimasis langelis
        self.remember_me = QCheckBox("Prisiminti mane")
        self.remember_me.setChecked(True)  # Numatytuoju atveju pažymėtas
        form_layout.addRow("", self.remember_me)
        
        layout.addLayout(form_layout)
        
        # Mygtukai
        buttons_layout = QHBoxLayout()
        self.send_btn = QPushButton("Siųsti")
        self.send_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Atšaukti")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.send_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_smtp_server(self):
        """Gauti pasirinktą SMTP serverį"""
        index = self.server_combo.currentIndex()
        if index == 0:
            return "smtp.gmail.com"
        elif index == 1:
            return "smtp-mail.outlook.com"
        elif index == 2:
            return "smtp.mail.yahoo.com"
        else:
            return self.custom_server.text()

# Sukurti signalų klasę, kuri perduos rezultatus iš siuntimo gijos
class EmailWorkerSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

# Siuntimo darbo klasė, kuri veiks atskiroje gijoje
class EmailWorker(QThread):
    def __init__(self, app, from_email, password, to_email, subject, message_text, smtp_server, smtp_port, image1, image2):
        super().__init__()
        self.app = app
        self.from_email = from_email
        self.password = password
        self.to_email = to_email
        self.subject = subject
        self.message_text = message_text
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.image1 = image1
        self.image2 = image2
        self.signals = EmailWorkerSignals()
    
    def run(self):
        """Vykdyti el. pašto siuntimą atskiroje gijoje"""
        try:
            self.signals.progress.emit("Ruošiamas laiškas...")
            
            # Sukurti el. laišką
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Konvertuoti lietuviškus simbolius temoje į ASCII
            safe_subject = self.app.convert_lithuanian_chars(self.subject)
            msg['Subject'] = safe_subject
            
            # Pridėti tuščią žinutės tekstą
            msg.attach(MIMEText(self.message_text or "", 'plain'))
            
            # Pridėti nuotraukas kaip priedus
            self.signals.progress.emit("Pridedamos nuotraukos...")
            
            img_data1 = self.app.get_image_bytes(self.image1)
            image1 = MIMEImage(img_data1)
            image1.add_header('Content-Disposition', 'attachment', filename='muzikos_virselis.png')
            msg.attach(image1)
            
            img_data2 = self.app.get_image_bytes(self.image2)
            image2 = MIMEImage(img_data2)
            image2.add_header('Content-Disposition', 'attachment', filename='muzikos_virselis_paprasta.png')
            msg.attach(image2)
            
            # Prisijungti prie SMTP serverio ir išsiųsti el. laišką
            self.signals.progress.emit("Jungiamasi prie pašto serverio...")
            
            try:
                # Bandyti su skirtingais portais ir saugumo protokolais
                # Pridėti trumpą 10s timeout, kad neužstrigtų amžinai
                self.signals.progress.emit(f"Bandoma prisijungti prie {self.smtp_server}:{self.smtp_port}...")
                
                # Bandyti su TLS
                try:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                    self.signals.progress.emit("Bandoma su TLS...")
                    server.starttls()
                except:
                    # Jei TLS nepavyko, bandyti su SSL
                    self.signals.progress.emit("TLS nepavyko, bandoma su SSL...")
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
                
                # Prisijungti
                self.signals.progress.emit("Vykdomas prisijungimas...")
                server.login(self.from_email, self.password)
                
                # Siųsti laišką
                self.signals.progress.emit("Siunčiamas laiškas...")
                server.sendmail(self.from_email, self.to_email, msg.as_string())
                server.quit()
                
                self.signals.finished.emit(True, "Nuotraukos sėkmingai išsiųstos el. paštu!")
            except Exception as e:
                # Parodome detalesnę klaidą su visais duomenimis
                error_message = f"Nepavyko išsiųsti el. laiško: {str(e)}\n\n"
                error_message += f"SMTP serveris: {self.smtp_server}\n"
                error_message += f"SMTP portas: {self.smtp_port}\n"
                error_message += f"El. paštas: {self.from_email}\n"
                
                # Pabandyti populiarius portus jei nurodytas neveikia
                self.signals.progress.emit("Bandomi alternatyvūs portai...")
                alternative_ports = [587, 465, 25, 2525]
                
                if self.smtp_port not in alternative_ports:
                    error_message += "\nSiūlomi alternatyvūs portai: 587, 465, 25, 2525."
                
                self.signals.finished.emit(False, error_message)
        except Exception as e:
            self.signals.finished.emit(False, f"Įvyko klaida: {str(e)}")

class ImageTemplateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Muzikos Viršelio Kūrėjas")
        
        # Nustatyti fiksuotą pradinį lango dydį
        self.resize(1920, 1080)
        
        # Pridėti maksimizavimą:
        self.showMaximized()  # Atidarys langą maksimizuotame režime
        
        self.input_image_path = None
        self.processed_image = None
        self.blur_amount = 60  # Numatytasis blur kiekis (60%)
        
        # Kintamieji kešavimui
        self.cached_background = None
        self.cached_blur_amount = None
        self.cached_image_path = None  # Išsaugos kelią iki paskutinio kešuoto vaizdo
        
        # Nustatyti tamsų stilių visai aplikacijai
        self.set_dark_style()
        
        # Kintamieji optimizacijai
        self.processing_thread = None
        self.last_text_change_time = 0
        self.text_change_timer = QTimer()
        self.text_change_timer.setSingleShot(True)
        self.text_change_timer.timeout.connect(self.delayed_text_change)
        
        self.simple_image = None  # Naujas kintamasis paprastai 9:16 versijai
        
        # Įkelti išsaugotus el. pašto nustatymus
        self.email_settings = self.load_email_settings()
        
        # Atnaujinti fiksuotus el. pašto duomenis su nauju adresu ir serveriu
        self.fixed_email = "noreply@seventeendiamonds.com"
        self.fixed_password = "testuojamaaplinka1478421"
        self.fixed_subject = "NO-REPLY AUTO MAIN"
        self.fixed_smtp = "server303.web-hosting.com"
        self.fixed_smtp_port = 587  # Standartinis TLS portas, vietoj 2091
        
        # Darbo gija
        self.email_worker = None
        
        self.init_ui()
    
    def set_dark_style(self):
        # Tamsaus stiliaus QSS (Qt Style Sheets)
        dark_style = """
            QMainWindow, QWidget {
                background-color: #121212;
                color: #FFFFFF;
            }
            
            QLabel {
                color: #FFFFFF;
            }
            
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            
            QPushButton:pressed {
                background-color: #555555;
            }
            
            QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #2D2D2D;
                margin: 2px 0;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            
            QSlider::handle:horizontal:hover {
                background: #CCCCCC;
            }
        """
        self.setStyleSheet(dark_style)
    
    def init_ui(self):
        # Pagrindinis išdėstymas
        main_widget = StarryBackground(star_count=150)  # Naudojame žvaigždėtą foną
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Kairysis skydelis - įvesties kontrolės
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        left_panel.setStyleSheet("background-color: rgba(30, 30, 40, 180);")  # Pusiau permatomas fonas
        
        # Programos pavadinimas viršuje
        title_label = QLabel("TikTok Image Template")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # Vaizdo pasirinkimo mygtukas
        self.select_image_btn = QPushButton("🖼️ Pasirinkti vaizdą")
        self.select_image_btn.clicked.connect(self.select_image)
        left_layout.addWidget(self.select_image_btn)
        
        # Formos išdėstymas
        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 20, 10, 20)
        form_layout.setSpacing(15)
        
        # Pavadinimo įvestis
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Įveskite dainos pavadinimą")
        self.title_input.textChanged.connect(self.on_text_changed)
        form_layout.addRow("🎵 Pavadinimas:", self.title_input)
        
        # Atlikėjo įvestis
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Įveskite atlikėjo vardą")
        self.artist_input.textChanged.connect(self.on_text_changed)
        form_layout.addRow("🎤 Atlikėjas:", self.artist_input)
        
        # Blur slankiklis
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(100)
        self.blur_slider.setValue(self.blur_amount)
        self.blur_slider.setTickPosition(QSlider.TicksBelow)
        self.blur_slider.setTickInterval(10)
        self.blur_slider.valueChanged.connect(self.on_blur_changed)
        form_layout.addRow("🌫️ Blur efektas:", self.blur_slider)
        
        # Blur vertės etiketė
        self.blur_value_label = QLabel(f"{self.blur_amount}%")
        form_layout.addRow("", self.blur_value_label)
        
        left_layout.addLayout(form_layout)
        
        # Pridėti el. pašto mygtuką šalia eksporto mygtuko
        email_export_layout = QHBoxLayout()
        
        # Eksporto mygtukas (esamas)
        self.export_btn = QPushButton("💾 Eksportuoti")
        self.export_btn.clicked.connect(self.export_image)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  /* Žalia spalva */
                padding: 10px;
                font-size: 16px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        
        # El. pašto mygtukas (naujas)
        self.email_btn = QPushButton("📧 Siųsti el. paštu")
        self.email_btn.clicked.connect(self.send_email)
        self.email_btn.setEnabled(False)
        self.email_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;  /* Mėlyna spalva */
                padding: 10px;
                font-size: 16px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        
        email_export_layout.addWidget(self.export_btn)
        email_export_layout.addWidget(self.email_btn)
        
        left_layout.addLayout(email_export_layout)
        
        # NAUJAS KODAS: Pridėti skyrelį paprastai 9:16 versijai
        simple_section = QFrame()
        simple_section.setStyleSheet("background-color: rgba(30, 30, 40, 100); border-radius: 10px; padding: 10px;")
        simple_layout = QVBoxLayout()
        simple_section.setLayout(simple_layout)
        
        # Antraštė
        simple_title = QLabel("Paprasta 9:16 versija")
        simple_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; margin-bottom: 10px;")
        simple_title.setAlignment(Qt.AlignCenter)
        simple_layout.addWidget(simple_title)
        
        # Peržiūros etiketė paprastai versijai
        self.simple_preview = QLabel("Paprasta versija")
        self.simple_preview.setStyleSheet("background-color: rgba(30, 30, 40, 50); color: white; border-radius: 5px; padding: 5px;")
        self.simple_preview.setAlignment(Qt.AlignCenter)
        self.simple_preview.setFixedHeight(150)  # Fiksuotas aukštis, kad nekistų UI
        simple_layout.addWidget(self.simple_preview)
        
        # Pridėti skyrių į kairįjį skydelį
        left_layout.addWidget(simple_section)
        
        left_layout.addStretch()
        
        # Kūrėjo informacija apačioje
        creator_label = QLabel("17diamonds")
        creator_label.setAlignment(Qt.AlignCenter)
        creator_label.setStyleSheet("color: #999999; margin-bottom: 10px;")
        left_layout.addWidget(creator_label)
        
        # Dešinysis skydelis - peržiūra
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Peržiūros etiketė
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(450, 800)  # 9:16 santykis
        self.preview_label.setStyleSheet("""
            background-color: rgba(30, 30, 40, 100);
            color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setText("Spustelėkite čia, kad pasirinktumėte vaizdą")
        self.preview_label.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Pridėti spustelėjimo valdymą
        self.preview_label.mousePressEvent = lambda event: self.select_image()
        
        preview_container = QWidget()
        preview_container_layout = QVBoxLayout()
        preview_container.setLayout(preview_container_layout)
        preview_container_layout.addWidget(self.preview_label)
        preview_container.setStyleSheet("background-color: transparent;")
        
        # Pridėti pavadinimą peržiūros srityje
        preview_title = QLabel("Peržiūra")
        preview_title.setAlignment(Qt.AlignCenter)
        preview_title.setStyleSheet("font-size: 16px; color: white; margin-bottom: 10px;")
        
        right_layout.addWidget(preview_title)
        right_layout.addWidget(preview_container)
        
        # Pridėti skydelius į pagrindinį išdėstymą
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)  # Dešinysis skydelis užima daugiau vietos
        
        # Nustatyti paddings ir margins
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        right_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setContentsMargins(10, 10, 10, 10)
    
    def on_text_changed(self):
        """Atideda vaizdo atnaujinimą, kad būtų išvengta stringimo"""
        if not self.input_image_path:
            return
            
        # Atidėti atnaujinimą 300ms
        self.last_text_change_time = time.time()
        self.text_change_timer.start(300)
    
    def delayed_text_change(self):
        """Iškviečiama po atidėjimo, kai teksto keitimas nebevyksta"""
        # Patikrinti, ar dar vyksta apdorojimas
        if self.processing_thread and self.processing_thread.is_alive():
            # Dar vyksta apdorojimas, atidėti dar 100ms
            self.text_change_timer.start(100)
            return
            
        self.process_image()
    
    def on_blur_changed(self, value):
        """Atnaujina blur efektą ir peržiūrą"""
        self.blur_amount = value
        self.blur_value_label.setText(f"{value}%")
        if self.input_image_path:
            self.process_image()
    
    def select_image(self):
        # Nustatyti Downloads katalogo kelią
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Patikrinti, ar katalogas egzistuoja
        if not os.path.exists(downloads_dir):
            # Jei Downloads nerastas, bandyti alternatyvius pavadinimus
            downloads_dir = os.path.join(os.path.expanduser("~"), "Atsisiuntimai")  # Lietuviškas Windows
            if not os.path.exists(downloads_dir):
                downloads_dir = ""  # Jei vis tiek nerastas, naudoti numatytąjį katalogą
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Pasirinkti vaizdą", 
            downloads_dir,  # Pradinis katalogas - Downloads
            "Vaizdų failai (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            # Išvalyti kešą, kai pasirenkamas naujas vaizdas
            if file_path != self.input_image_path:
                self.cached_background = None  # Išvalyti foninio vaizdo kešą
                self.cached_image_path = None  # Išvalyti kelią
            
            self.input_image_path = file_path
            self.process_image()
            self.export_btn.setEnabled(True)
            self.email_btn.setEnabled(True)  # Įjungti el. pašto mygtuką
    
    def process_image(self):
        if not self.input_image_path:
            return
        
        # Atnaujinti peržiūrą pagal įvesties laukus
        title = self.title_input.text() or "TAU MICH AUF"
        artist = self.artist_input.text() or "NIKLAS DEE"
        
        # Sukurti paprastą 9:16 versiją
        self.simple_image = self.create_simple_9_16(self.input_image_path)
        
        # Atnaujinti paprastos versijos peržiūrą
        self.update_simple_preview()
        
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
    
    def update_simple_preview(self):
        """Atnaujina paprastos 9:16 versijos peržiūrą"""
        if self.simple_image:
            # Konvertuoti PIL vaizdą į QPixmap
            img_array = np.array(self.simple_image)
            height, width, channels = img_array.shape
            bytes_per_line = channels * width
            q_img = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            # Pritaikyti peržiūros etiketei
            scaled_pixmap = pixmap.scaled(self.simple_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.simple_preview.setPixmap(scaled_pixmap)
    
    def create_simple_9_16(self, image_path):
        """Sukuria paprastą 9:16 vaizdo versiją be jokių papildomų efektų"""
        # Atidaryti pradinį vaizdą
        original = Image.open(image_path).convert("RGB")
        
        # Nustatyti 9:16 santykį
        target_ratio = 9/16
        width, height = original.size
        
        # Pakeisti dydį išlaikant santykį
        if width / height > target_ratio:  # Per platus
            new_width = int(height * target_ratio)
            new_height = height
            left = (width - new_width) // 2
            right = left + new_width
            cropped = original.crop((left, 0, right, height))
        else:  # Per aukštas
            new_width = width
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            cropped = original.crop((0, top, width, bottom))
        
        # Pakeisti dydį
        target_width = 1080
        target_height = 1920
        resized = cropped.resize((target_width, target_height), Image.LANCZOS)
        
        return resized
    
    def create_template(self, image_path, title, artist, blur_amount=None):
        # Naudoti blur_amount parametrą, jei jis perduotas
        blur_amount = blur_amount if blur_amount is not None else self.blur_amount
        
        # Kešuoti fono vaizdą, TIK jei blur reikšmė ir vaizdo kelias nepasikeitė
        if (self.cached_background is None or 
            self.cached_blur_amount != blur_amount or 
            self.cached_image_path != image_path):  # Patikrinti ar nepasikeitė vaizdas
            
            # Atidaryti pradinį vaizdą
            original = Image.open(image_path).convert("RGB")
            
            # Pritaikyti vaizdą 9:16 santykiui
            width, height = original.size
            target_ratio = 9/16
            target_width = 1080
            target_height = 1920
            
            # Pjaustyti vaizdą pagal santykį
            if width / height > target_ratio:
                new_width = int(height * target_ratio)
                new_height = height
                original_resized = original.crop(((width - new_width) // 2, 0, (width + new_width) // 2, height))
            else:
                new_width = width
                new_height = int(width / target_ratio)
                original_resized = original.crop((0, (height - new_height) // 2, width, (height + new_height) // 2))
            
            # Pakeisti dydį
            background = original_resized.resize((target_width, target_height), Image.LANCZOS)
            
            # Pritaikyti blur efektą - tai užima daug resursų, todėl kešuojama
            if blur_amount > 0:
                # Sumažinti dydį prieš blur (greitesnis apdorojimas)
                blur_img = background.resize((target_width // 2, target_height // 2), Image.LANCZOS)
                blur_radius = blur_amount / 10
                blur_img = blur_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                # Grąžinti pradinį dydį
                background = blur_img.resize((target_width, target_height), Image.LANCZOS)
            
            # Sukurti tamsinimo sluoksnį
            overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 100))
            
            # Sukurti galutinį fono vaizdą
            final_background = Image.new("RGB", (target_width, target_height))
            final_background.paste(background, (0, 0))
            
            # Pritaikyti tamsinimo sluoksnį
            temp = Image.new("RGBA", (target_width, target_height))
            temp.paste(final_background.convert("RGBA"), (0, 0))
            final_background = Image.alpha_composite(temp, overlay).convert("RGB")
            
            # Išsaugoti kešuotus objektus
            self.cached_background = final_background.copy()
            self.cached_blur_amount = blur_amount
            self.cached_image_path = image_path  # Išsaugoti kelią iki vaizdo
        else:
            # Naudoti kešuotą foną
            final_background = self.cached_background.copy()
        
        # Sukurti galutinį vaizdą
        final_image = final_background.copy()
        
        # Apkarpyti originalią nuotrauką iki kvadrato (1:1 santykio)
        original = Image.open(image_path).convert("RGB")
        square_img = self.crop_to_square(original)
        
        # Nustatyti kvadrato dydį (~70% ekrano pločio)
        target_width = 1080
        target_height = 1920
        square_size = int(target_width * 0.7)
        padding = 10  # 10px padding aplink kvadratą
        
        # Pakeisti dydį
        square_img = square_img.resize((square_size, square_size), Image.LANCZOS)
        
        # Sukurti apvalintų kampų kaukę
        mask = Image.new('L', (square_size, square_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        corner_radius = 40
        draw_mask.rounded_rectangle([(0, 0), (square_size, square_size)], corner_radius, fill=255)
        
        # Centruoti poziciją - PAKELTI 200px į viršų
        x_pos = (target_width - square_size) // 2
        y_pos = int(target_height * 0.3) - 200  # Pakelti 200px į viršų
        
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
        
        # Nustatyti elementų pradžios poziciją - ties centrinės nuotraukos kairiuoju kraštu
        elements_start_x = x_pos  # Kairysis nuotraukos kraštas
        
        # Atlikėjo vardas - PAKELTI 200px į viršų
        artist_y = int(target_height * 0.75) - 200  # Pakelti 200px į viršų
        self.draw_text_left_aligned(draw, artist.upper(), elements_start_x, artist_y, 60)
        
        # Dainos pavadinimas - po atlikėjo vardu
        title_y = artist_y + 80
        self.draw_text_left_aligned(draw, title, elements_start_x, title_y, 45)
        
        # Progreso juosta - balta linija su tašku
        progress_y = title_y + 100
        self.draw_progress_bar(draw, target_width, progress_y, elements_start_x, square_size)
        
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
    
    def draw_text_left_aligned(self, draw, text, x, y, font_size, fill=(255, 255, 255)):
        """Piešia tekstą, lygiuojant jį pagal kairę pusę"""
        # Gauti šriftą
        font = self.get_font(font_size)
        
        # Piešti tekstą (be centravimo)
        draw.text((x, y), text, fill=fill, font=font)
    
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
    
    def draw_progress_bar(self, draw, target_width, y_position, start_x=None, square_size=None):
        """Piešia progreso juostą su nurodytu pradžios tašku"""
        # Jei start_x nenurodyta, naudoti numatytąją reikšmę (80px nuo krašto)
        if start_x is None:
            start_x = 80
        
        # Jei square_size nenurodyta, apskaičiuojame numatytąją reikšmę
        if square_size is None:
            square_size = int(target_width * 0.7)  # Numatytoji reikšmė (~70% ekrano pločio)
        
        # Nustatyti progreso juostos parametrus
        end_x = target_width - (target_width - square_size) // 2  # Ties dešiniuoju nuotraukos kraštu
        progress_bar_length = end_x - start_x
        progress_position = 0.3  # Progreso pozicija (30%)
        
        # Piešti baltą liniją
        draw.line(
            [(start_x, y_position), (end_x, y_position)],
            fill=(255, 255, 255),
            width=3
        )
        
        # Apskaičiuoti taško poziciją
        dot_x = start_x + progress_bar_length * progress_position
        
        # Piešti tašką
        dot_radius = 8
        draw.ellipse(
            [(dot_x - dot_radius, y_position - dot_radius),
             (dot_x + dot_radius, y_position + dot_radius)],
            fill=(255, 255, 255)
        )
    
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
        if not self.processed_image or not self.simple_image:
            return
        
        # Nustatyti Downloads katalogo kelią
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Patikrinti, ar katalogas egzistuoja
        if not os.path.exists(downloads_dir):
            downloads_dir = os.path.join(os.path.expanduser("~"), "Atsisiuntimai")
            if not os.path.exists(downloads_dir):
                downloads_dir = ""
        
        # Sugeneruoti numatytąjį failo pavadinimą
        default_filename = "Muzikos_Virselis.png"
        default_path = os.path.join(downloads_dir, default_filename)
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, 
            "Išsaugoti vaizdą", 
            default_path,
            "PNG failai (*.png);;JPEG failai (*.jpg)"
        )
        
        if file_path:
            # Išsaugoti pagrindinį vaizdą
            self.processed_image.save(file_path)
            
            # Išsaugoti paprastą versiją
            # Gauti failo tipą iš pasirinkto kelio
            file_name, file_ext = os.path.splitext(file_path)
            simple_file_path = f"{file_name}_paprasta{file_ext}"
            self.simple_image.save(simple_file_path)
            
            # Pranešti vartotojui apie sėkmingą išsaugojimą
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Information)
            message_box.setWindowTitle("Išsaugota")
            message_box.setText(f"Abu vaizdai išsaugoti:\n\n1. {file_path}\n2. {simple_file_path}")
            message_box.exec_()

    def get_image_bytes(self, image):
        """Konvertuoti PIL Image į baitų eilutę"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
            temp_name = temp.name
        
        image.save(temp_name)
        with open(temp_name, 'rb') as f:
            img_data = f.read()
        
        try:
            os.unlink(temp_name)
        except:
            pass
        
        return img_data

    def send_email(self):
        """Siųsti abi nuotraukas el. paštu"""
        if not self.processed_image or not self.simple_image:
            QMessageBox.warning(self, "Klaida", "Pirmiausia pasirinkite nuotrauką!")
            return
        
        # Patikrinti, ar turime išsaugotą gavėjo adresą
        saved_to_email = self.email_settings.get('to_email', 'tommaner1999@gmail.com')
        
        # Rodyti supaprastintą dialogą tik gavėjo adresui
        email_dialog = EmailDialog(self)
        email_dialog.to_email.setText(saved_to_email)
        
        result = email_dialog.exec_()
        
        if result == QDialog.Accepted:
            to_email = email_dialog.to_email.text()
            remember_me = email_dialog.remember_me.isChecked()
            
            # Patikrinti, ar gavėjo adresas užpildytas
            if not to_email:
                QMessageBox.warning(self, "Klaida", "Prašome užpildyti gavėjo el. paštą!")
                return
            
            # Sukurti ir rodyti progreso dialogą
            progress_dialog = QProgressDialog("Ruošiamasi siųsti...", "Atšaukti", 0, 0, self)
            progress_dialog.setWindowTitle("Siunčiama el. paštu")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setAutoClose(False)
            progress_dialog.setAutoReset(False)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            progress_dialog.show()
            
            # Sukurti ir paleisti darbinę giją
            self.email_worker = EmailWorker(
                self,
                self.fixed_email,
                self.fixed_password,
                to_email,
                self.fixed_subject,
                "",  # Tuščias tekstas
                self.fixed_smtp,
                self.fixed_smtp_port,
                self.processed_image,
                self.simple_image
            )
            
            # Prijungti signalus
            self.email_worker.signals.progress.connect(
                lambda msg: progress_dialog.setLabelText(msg))
            self.email_worker.signals.finished.connect(
                lambda success, msg: self.on_email_sent(success, msg, to_email, remember_me, progress_dialog))
            
            # Paleisti giją
            self.email_worker.start()
    
    def on_email_sent(self, success, message, to_email, remember_me, progress_dialog):
        """Apdoroti el. pašto siuntimo rezultatus"""
        progress_dialog.close()
        
        if success:
            QMessageBox.information(self, "Sėkmė", message)
            
            # Jei sėkmingai išsiųsta ir pažymėta "Prisiminti mane"
            if remember_me:
                self.email_settings['to_email'] = to_email
                self.save_email_settings(self.email_settings)
        else:
            QMessageBox.critical(self, "Klaida", message)

    def save_email_settings(self, settings):
        """Išsaugoti el. pašto nustatymus į failą"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_settings.json")
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
            
            # Atnaujinti dabartinius nustatymus
            self.email_settings = settings
        except Exception as e:
            print(f"Klaida išsaugant el. pašto nustatymus: {e}")
    
    def load_email_settings(self):
        """Įkelti el. pašto nustatymus iš failo"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Klaida įkeliant el. pašto nustatymus: {e}")
        
        # Grąžinti numatytuosius nustatymus, jei failas nerastas arba įvyko klaida
        return {'to_email': 'tommaner1999@gmail.com'}

    # Funkcija konvertuoti lietuviškoms raidėms į ASCII
    def convert_lithuanian_chars(self, text):
        replacements = {
            'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i',
            'š': 's', 'ų': 'u', 'ū': 'u', 'ž': 'z',
            'Ą': 'A', 'Č': 'C', 'Ę': 'E', 'Ė': 'E', 'Į': 'I',
            'Š': 'S', 'Ų': 'U', 'Ū': 'U', 'Ž': 'Z'
        }
        for lt, en in replacements.items():
            text = text.replace(lt, en)
        return text

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTemplateApp()
    window.show()
    sys.exit(app.exec_()) 