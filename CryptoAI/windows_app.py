"""
Native Windows Application for CryptoAI
System tray app with notifications and auto-start support
"""
import sys
import os
import threading
import webbrowser
from datetime import datetime

# Windows-specific imports
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    
    # For toast notifications on Windows 10/11
    try:
        from win10toast import ToastNotifier
        HAS_TOAST = True
    except ImportError:
        HAS_TOAST = False
    
    # For system tray
    try:
        import pystray
        from PIL import Image, ImageDraw
        HAS_TRAY = True
    except ImportError:
        HAS_TRAY = False
else:
    HAS_TOAST = False
    HAS_TRAY = False

# Import our modules
try:
    from portfolio import Portfolio
    from data_fetcher import LiveDataFetcher
    from mobile_api import run_api
except ImportError as e:
    print(f"Import error: {e}")


class WindowsCryptoApp:
    """Native Windows application with system tray and notifications"""
    
    def __init__(self):
        self.portfolio = Portfolio()
        self.data_fetcher = LiveDataFetcher()
        self.running = True
        self.api_thread = None
        self.monitor_thread = None
        self.icon = None
        
        # Notification settings
        self.notify_on_price_change = True
        self.price_alert_threshold = 5.0  # 5% change
        self.last_prices = {}
        
        if HAS_TOAST:
            self.toaster = ToastNotifier()
        
    def create_tray_icon(self) -> Image.Image:
        """Create a simple icon for system tray"""
        # Create a simple coin icon
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a gold coin
        draw.ellipse([4, 4, size-4, size-4], fill='#FFD700', outline='#B8860B', width=3)
        
        # Draw $ symbol
        draw.text((size//2-8, size//2-12), '$', fill='#B8860B')
        
        return image
    
    def send_notification(self, title: str, message: str, duration: int = 5):
        """Send Windows toast notification"""
        if HAS_TOAST:
            try:
                self.toaster.show_toast(
                    title,
                    message,
                    duration=duration,
                    threaded=True
                )
            except Exception as e:
                print(f"Notification error: {e}")
        else:
            print(f"[NOTIFICATION] {title}: {message}")
    
    def check_price_alerts(self):
        """Check for significant price changes and send alerts"""
        try:
            # Get prices for portfolio positions
            coin_ids = list(self.portfolio.positions.keys())
            if not coin_ids:
                return
            
            prices = self.data_fetcher.get_live_prices(coin_ids)
            
            for coin_id, price_data in prices.items():
                current_price = price_data if isinstance(price_data, (int, float)) else price_data.get('price', 0)
                
                if coin_id in self.last_prices:
                    last_price = self.last_prices[coin_id]
                    if last_price > 0:
                        change_pct = ((current_price - last_price) / last_price) * 100
                        
                        if abs(change_pct) >= self.price_alert_threshold:
                            direction = "📈 UP" if change_pct > 0 else "📉 DOWN"
                            self.send_notification(
                                f"CryptoAI Alert: {coin_id.upper()}",
                                f"{direction} {abs(change_pct):.1f}%\nPrice: ${current_price:,.2f}"
                            )
                
                self.last_prices[coin_id] = current_price
                
        except Exception as e:
            print(f"Price check error: {e}")
    
    def monitor_loop(self):
        """Background monitoring loop"""
        import time
        
        while self.running:
            try:
                self.check_price_alerts()
                
                # Update portfolio prices
                coin_ids = list(self.portfolio.positions.keys())
                if coin_ids:
                    prices = self.data_fetcher.get_live_prices(coin_ids)
                    formatted_prices = {}
                    for cid, p in prices.items():
                        if isinstance(p, (int, float)):
                            formatted_prices[cid] = {'price': p}
                        else:
                            formatted_prices[cid] = p
                    self.portfolio.update_prices(formatted_prices)
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            # Check every 60 seconds
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)
    
    def start_api_server(self):
        """Start the REST API in background"""
        try:
            run_api(host='127.0.0.1', port=5000, debug=False)
        except Exception as e:
            print(f"API server error: {e}")
    
    def open_dashboard(self):
        """Open the web dashboard"""
        webbrowser.open('http://localhost:8050')
    
    def open_api_docs(self):
        """Open API documentation"""
        webbrowser.open('http://localhost:5000/api/v1')
    
    def show_portfolio_summary(self):
        """Show portfolio summary notification"""
        perf = self.portfolio.get_portfolio_performance()
        self.send_notification(
            "CryptoAI Portfolio",
            f"Value: ${perf['current_value']:,.2f}\n"
            f"Return: {perf['return_percent']:+.1f}%\n"
            f"Positions: {perf['num_positions']}",
            duration=10
        )
    
    def quit_app(self):
        """Quit the application"""
        self.running = False
        if self.icon:
            self.icon.stop()
    
    def create_menu(self):
        """Create system tray menu"""
        if not HAS_TRAY:
            return None
        
        return pystray.Menu(
            pystray.MenuItem("📊 Open Dashboard", lambda: self.open_dashboard()),
            pystray.MenuItem("🔌 API Documentation", lambda: self.open_api_docs()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("💰 Portfolio Summary", lambda: self.show_portfolio_summary()),
            pystray.MenuItem("🔔 Price Alerts", pystray.Menu(
                pystray.MenuItem("Enabled", lambda item: self.toggle_alerts(), 
                               checked=lambda item: self.notify_on_price_change),
                pystray.MenuItem("5% threshold", lambda: self.set_threshold(5)),
                pystray.MenuItem("10% threshold", lambda: self.set_threshold(10)),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Quit", lambda: self.quit_app())
        )
    
    def toggle_alerts(self):
        """Toggle price alerts"""
        self.notify_on_price_change = not self.notify_on_price_change
        status = "enabled" if self.notify_on_price_change else "disabled"
        self.send_notification("CryptoAI", f"Price alerts {status}")
    
    def set_threshold(self, pct: float):
        """Set price alert threshold"""
        self.price_alert_threshold = pct
        self.send_notification("CryptoAI", f"Alert threshold set to {pct}%")
    
    def run(self):
        """Run the Windows application"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║              🪙 CryptoAI Windows Application                 ║
╠══════════════════════════════════════════════════════════════╣
║  Starting services...                                        ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Start API server in background
        self.api_thread = threading.Thread(target=self.start_api_server, daemon=True)
        self.api_thread.start()
        print("✓ REST API started on http://localhost:5000")
        
        # Start monitoring in background
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✓ Price monitoring started")
        
        # Send startup notification
        self.send_notification(
            "CryptoAI Started",
            "Portfolio tracker is running in the system tray"
        )
        
        if HAS_TRAY:
            # Create and run system tray icon
            self.icon = pystray.Icon(
                "CryptoAI",
                self.create_tray_icon(),
                "CryptoAI Portfolio Tracker",
                self.create_menu()
            )
            print("✓ System tray icon created")
            print("\n📌 CryptoAI is running in the system tray!")
            self.icon.run()
        else:
            print("\n⚠️ System tray not available. Running in console mode.")
            print("Press Ctrl+C to quit.\n")
            try:
                while self.running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.quit_app()


def add_to_startup():
    """Add CryptoAI to Windows startup"""
    if sys.platform != 'win32':
        print("This function is only available on Windows")
        return False
    
    import winreg
    
    # Get the path to this script
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    
    # Command to run
    command = f'"{python_path}" "{script_path}"'
    
    try:
        # Open the registry key for startup programs
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Add our entry
        winreg.SetValueEx(key, "CryptoAI", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        
        print("✓ CryptoAI added to Windows startup")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add to startup: {e}")
        return False


def remove_from_startup():
    """Remove CryptoAI from Windows startup"""
    if sys.platform != 'win32':
        print("This function is only available on Windows")
        return False
    
    import winreg
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        winreg.DeleteValue(key, "CryptoAI")
        winreg.CloseKey(key)
        
        print("✓ CryptoAI removed from Windows startup")
        return True
        
    except FileNotFoundError:
        print("CryptoAI is not in startup")
        return False
    except Exception as e:
        print(f"❌ Failed to remove from startup: {e}")
        return False


def create_desktop_shortcut():
    """Create a desktop shortcut for CryptoAI"""
    if sys.platform != 'win32':
        print("This function is only available on Windows")
        return False
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "CryptoAI.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
        shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        shortcut.Description = "CryptoAI Portfolio Tracker"
        shortcut.save()
        
        print(f"✓ Desktop shortcut created: {shortcut_path}")
        return True
        
    except ImportError:
        print("⚠️ Install pywin32 and winshell: pip install pywin32 winshell")
        return False
    except Exception as e:
        print(f"❌ Failed to create shortcut: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CryptoAI Windows Application')
    parser.add_argument('--add-startup', action='store_true', help='Add to Windows startup')
    parser.add_argument('--remove-startup', action='store_true', help='Remove from Windows startup')
    parser.add_argument('--create-shortcut', action='store_true', help='Create desktop shortcut')
    parser.add_argument('--console', action='store_true', help='Run in console mode (no tray)')
    
    args = parser.parse_args()
    
    if args.add_startup:
        add_to_startup()
    elif args.remove_startup:
        remove_from_startup()
    elif args.create_shortcut:
        create_desktop_shortcut()
    else:
        app = WindowsCryptoApp()
        app.run()
