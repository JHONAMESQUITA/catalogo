import os
import io
import base64
import socketio
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from PIL import Image as PILImage

sio = socketio.Client()
# ─────────────────────────────────────────────────
# CAMBIA ESTO por la URL de tu servidor en la nube
# Ejemplo: SERVER_URL = 'https://catalogo.onrender.com'
# ─────────────────────────────────────────────────
SERVER_URL = 'http://127.0.0.1:5000'  # Local (desarrollo)

class SenderApp(App):
    def build(self):
        Window.size = (480, 720)
        self.selected_path = None
        self.connected = False

        layout = BoxLayout(orientation='vertical', spacing=12, padding=16)

        self.status_label = Label(
            text='Desconectado',
            size_hint=(1, 0.06),
            color=(1, 0.3, 0.3, 1),
            font_size=16,
            bold=True
        )
        layout.add_widget(self.status_label)

        self.preview = Image(
            size_hint=(1, 0.4),
            fit_mode='contain'
        )
        layout.add_widget(self.preview)

        self.select_btn = Button(
            text='Seleccionar Imagen',
            size_hint=(1, 0.07),
            background_color=(0.2, 0.4, 0.8, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            bold=True
        )
        self.select_btn.bind(on_press=self.select_image)
        layout.add_widget(self.select_btn)

        self.file_label = Label(
            text='Ninguna imagen seleccionada',
            size_hint=(1, 0.04),
            color=(0.6, 0.6, 0.6, 1),
            font_size=13
        )
        layout.add_widget(self.file_label)

        cat_layout = BoxLayout(orientation='horizontal', spacing=8, size_hint=(1, 0.07))
        self.category_buttons = {}
        for cat in ['tarima', 'carpa', 'hangar', 'varios']:
            btn = Button(
                text=cat.capitalize(),
                background_color=(0.3, 0.3, 0.3, 1),
                color=(1, 1, 1, 1),
                font_size=14,
                bold=True
            )
            btn.bind(on_press=lambda x, c=cat: self.set_category(c))
            self.category_buttons[cat] = btn
            cat_layout.add_widget(btn)
        layout.add_widget(cat_layout)

        self.selected_category = 'varios'
        self.category_buttons['varios'].background_color = (0.9, 0.3, 0.3, 1)

        self.send_btn = Button(
            text='Enviar Imagen',
            size_hint=(1, 0.1),
            background_color=(0.1, 0.7, 0.3, 1),
            color=(1, 1, 1, 1),
            font_size=18,
            bold=True,
            disabled=True
        )
        self.send_btn.bind(on_press=self.send_image)
        layout.add_widget(self.send_btn)

        Clock.schedule_interval(self.check_connection, 1)
        Clock.schedule_once(lambda dt: self.connect_server(), 0.5)

        return layout

    def connect_server(self):
        try:
            sio.connect(SERVER_URL, wait_timeout=5)
            self.connected = True
            Clock.schedule_once(lambda dt: self.update_status('Conectado', (0.3, 1, 0.3, 1)), 0)
        except Exception as e:
            self.connected = False
            Clock.schedule_once(lambda dt: self.update_status(f'Error: {str(e)[:30]}', (1, 0.3, 0.3, 1)), 0)

    def check_connection(self, dt):
        if sio.connected and not self.connected:
            self.connected = True
            self.update_status('Conectado', (0.3, 1, 0.3, 1))
        elif not sio.connected and self.connected:
            self.connected = False
            self.update_status('Desconectado', (1, 0.3, 0.3, 1))

    def update_status(self, text, color):
        self.status_label.text = text
        self.status_label.color = color

    def set_category(self, cat):
        self.selected_category = cat
        for c, btn in self.category_buttons.items():
            btn.background_color = (0.9, 0.3, 0.3, 1) if c == cat else (0.3, 0.3, 0.3, 1)

    def select_image(self, instance):
        content = BoxLayout(orientation='vertical', spacing=8, padding=8)
        filechooser = FileChooserListView(
            filters=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp'],
            path=os.path.expanduser('~')
        )
        content.add_widget(filechooser)

        btn_layout = BoxLayout(size_hint=(1, 0.12), spacing=8)
        select_btn = Button(text='Seleccionar', bold=True)
        cancel_btn = Button(text='Cancelar', bold=True)
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Seleccionar Imagen', content=content, size_hint=(0.9, 0.9))

        def on_select(btn):
            if filechooser.selection:
                self.selected_path = filechooser.selection[0]
                self.file_label.text = os.path.basename(self.selected_path)
                self.preview.source = self.selected_path
                self.preview.reload()
                self.send_btn.disabled = False
            popup.dismiss()

        def on_cancel(btn):
            popup.dismiss()

        select_btn.bind(on_press=on_select)
        cancel_btn.bind(on_press=on_cancel)
        popup.open()

    def send_image(self, instance):
        if not self.selected_path or not os.path.exists(self.selected_path):
            return

        try:
            img = PILImage.open(self.selected_path)
            img.thumbnail((1024, 1024))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            sio.emit('upload_image', {
                'category': self.selected_category,
                'image': img_base64,
                'name': os.path.basename(self.selected_path)
            })

            content = Label(text=f'Imagen enviada a {self.selected_category.upper()}')
            popup = Popup(title='Enviado', content=content, size_hint=(0.6, 0.3))
            popup.open()
            Clock.schedule_once(lambda dt: popup.dismiss(), 2)
        except Exception as e:
            content = Label(text=f'Error: {str(e)[:40]}')
            popup = Popup(title='Error', content=content, size_hint=(0.6, 0.3))
            popup.open()

    def on_stop(self):
        if sio.connected:
            sio.disconnect()

if __name__ == '__main__':
    SenderApp().run()
