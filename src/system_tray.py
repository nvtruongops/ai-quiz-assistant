"""
System Tray Module
Manages system tray icon and menu
"""

import pystray
from PIL import Image, ImageDraw, ImageFont
from threading import Thread


class SystemTray:
    """Manages system tray icon and menu"""
    
    def __init__(self, app):
        """
        Initialize SystemTray
        
        Args:
            app: QuizAssistantApp instance
        """
        self.app = app
        self.icon = None
        self._running = False
    
    def create_icon(self) -> Image.Image:
        """
        Create simple system tray icon using PIL
        Draw "Q" letter on background
        
        Returns:
            PIL Image object for icon
        """
        # Create 64x64 image with blue background
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='#0066CC')
        
        # Create draw object
        draw = ImageDraw.Draw(image)
        
        # Draw white "Q" letter in center
        # Use default font since no font file available
        try:
            # Try to load font with large size
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Calculate position to center "Q" letter
        text = "Q"
        
        # Use textbbox to calculate text size
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback for older PIL versions
            text_width = 30
            text_height = 30
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw "Q" letter
        draw.text((x, y), text, fill='white', font=font)
        
        return image
    
    def create_menu(self) -> pystray.Menu:
        """
        Create context menu with items:
        - "Status: Running"
        - separator
        - "Exit"
        
        Returns:
            pystray.Menu object
        """
        return pystray.Menu(
            pystray.MenuItem(
                "Status: Running",
                lambda: None,  # Non-clickable status item
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Exit",
                self.on_quit
            )
        )
    
    def on_quit(self, icon=None, item=None):
        """
        Handle event when user selects "Exit" from menu
        Stop application
        
        Args:
            icon: pystray.Icon object (optional)
            item: Menu item clicked (optional)
        """
        if self.icon:
            self.icon.stop()
        
        # Stop application
        if self.app:
            self.app.stop()
    
    def show_notification(self, title: str, message: str):
        """
        Show notification from system tray (optional)
        
        Args:
            title: Notification title
            message: Notification content
        """
        if self.icon and self.icon.visible:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                # Notification not supported on some systems
                pass
    
    def run(self):
        """
        Run system tray in separate thread
        Create icon and menu, then run event loop
        """
        if self._running:
            return
        
        self._running = True
        
        # Create icon image
        icon_image = self.create_icon()
        
        # Create menu
        menu = self.create_menu()
        
        # Create pystray.Icon
        self.icon = pystray.Icon(
            "QuizAssistant",
            icon_image,
            "AI Quiz Assistant",
            menu
        )
        
        # Run icon (blocking call)
        self.icon.run()
    
    def start(self):
        """
        Start system tray in separate thread
        """
        if not self._running:
            thread = Thread(target=self.run, daemon=True)
            thread.start()
    
    def stop(self):
        """
        Stop system tray
        """
        if self.icon:
            self.icon.stop()
        self._running = False
