import customtkinter as ctk
from tkinter import filedialog, scrolledtext, messagebox
import tkinter as tk
import subprocess
import threading
import os
import sys
import requests
import platform
import shutil

# Set appearance mode and color theme
ctk.set_appearance_mode("system")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Debug flag - set to True to force download dialog even if gallery-dl is found
FORCE_DOWNLOAD_DIALOG = False

class GalleryDLUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gallery-DL UI")
        self.root.geometry("1000x800")
        
        # Configure root window
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Gallery-dl executable path
        self.gallery_dl_path = self.find_gallery_dl()
        
        # Check for gallery-dl on startup (or force dialog if debug flag is set)
        if not self.gallery_dl_path or FORCE_DOWNLOAD_DIALOG:
            if FORCE_DOWNLOAD_DIALOG:
                self.log_to_console_if_exists("Debug mode: Forcing download dialog")
            self.show_download_dialog()
        
        # Create main container
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create a tabbed interface
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))
        
        # Create tabs for different categories of options
        self.create_main_tab()
        self.create_general_options_tab()
        self.create_input_options_tab()
        self.create_output_options_tab()
        self.create_networking_tab()
        self.create_download_tab()
        self.create_auth_tab()
        self.create_selection_tab()
        self.create_postprocessing_tab()
        
        # Output console
        self.create_console()
        
        # Run button
        self.run_button = ctk.CTkButton(
            self.main_frame, 
            text="Run Download", 
            command=self.run_gallery_dl,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.run_button.grid(row=2, column=0, pady=20)

    def find_gallery_dl(self):
        """Find gallery-dl executable in various locations."""
        # If debug flag is set, pretend gallery-dl is not found
        if FORCE_DOWNLOAD_DIALOG:
            return None
            
        possible_names = ["gallery-dl", "gallery-dl.exe"]
        
        # Check current directory first
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for name in possible_names:
            path = os.path.join(current_dir, name)
            if os.path.isfile(path):
                return path
        
        # Check if gallery-dl is in PATH
        for name in possible_names:
            if shutil.which(name):
                return name
        
        return None

    def get_download_url(self):
        """Get the appropriate download URL based on platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        base_url = "https://github.com/mikf/gallery-dl/releases/download/v1.29.7/"
        
        if system == "windows":
            if machine in ["amd64", "x86_64"]:
                return base_url + "gallery-dl.exe"
            else:
                return base_url + "gallery-dl_x86.exe"
        elif system in ["linux", "darwin"]:  # Linux or macOS
            return base_url + "gallery-dl.bin"
        else:
            # Fallback to Python wheel
            return base_url + "gallery_dl-1.29.7-py3-none-any.whl"

    def show_download_dialog(self):
        """Show dialog asking user to download gallery-dl."""
        result = messagebox.askyesno(
            "Gallery-DL Not Found",
            "Gallery-DL executable was not found on your system.\n\n"
            "Would you like to download the latest binary to the current directory?\n\n"
            "This will download the appropriate version for your platform.",
            icon="question"
        )
        
        if result:
            self.download_gallery_dl()

    def download_gallery_dl(self):
        """Download gallery-dl binary in a separate thread."""
        def download_worker():
            try:
                url = self.get_download_url()
                filename = os.path.basename(url)
                
                # Determine the local filename
                if filename.endswith(".whl"):
                    local_filename = "gallery-dl"  # We'll need to handle wheel installation
                elif filename == "gallery-dl.bin":
                    local_filename = "gallery-dl"
                else:
                    local_filename = filename
                
                current_dir = os.path.dirname(os.path.abspath(__file__))
                local_path = os.path.join(current_dir, local_filename)
                
                # Show progress in console
                self.root.after(0, lambda: self.log_to_console(f"Downloading gallery-dl from {url}..."))
                
                # Download the file
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                self.root.after(0, lambda p=progress: self.log_to_console(f"Download progress: {p:.1f}%"))
                
                # Make executable on Unix-like systems
                if not filename.endswith((".exe", ".whl")):
                    os.chmod(local_path, 0o755)
                
                # Handle wheel installation
                if filename.endswith(".whl"):
                    self.root.after(0, lambda: self.log_to_console("Installing gallery-dl from wheel..."))
                    result = subprocess.run([sys.executable, "-m", "pip", "install", local_path], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        self.gallery_dl_path = "gallery-dl"
                        self.root.after(0, lambda: self.log_to_console("Gallery-dl installed successfully via pip!"))
                        os.remove(local_path)  # Remove the wheel file
                    else:
                        self.root.after(0, lambda: self.log_to_console(f"Failed to install wheel: {result.stderr}"))
                        return
                else:
                    self.gallery_dl_path = local_path
                    self.root.after(0, lambda: self.log_to_console(f"Gallery-dl downloaded successfully to {local_path}"))
                
                # Test the installation
                self.root.after(0, self.test_gallery_dl)
                
            except Exception as e:
                self.root.after(0, lambda: self.log_to_console(f"Failed to download gallery-dl: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror(
                    "Download Failed", 
                    f"Failed to download gallery-dl:\n{str(e)}\n\n"
                    "Please download manually from:\n"
                    "https://github.com/mikf/gallery-dl/releases"
                ))
        
        # Start download in background thread
        threading.Thread(target=download_worker, daemon=True).start()

    def test_gallery_dl(self):
        """Test if gallery-dl is working."""
        if not self.gallery_dl_path:
            return
        
        try:
            result = subprocess.run([self.gallery_dl_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log_to_console(f"Gallery-dl is ready: {version}")
                messagebox.showinfo("Success", f"Gallery-dl is ready!\n{version}")
            else:
                self.log_to_console(f"Gallery-dl test failed: {result.stderr}")
        except Exception as e:
            self.log_to_console(f"Failed to test gallery-dl: {str(e)}")

    def create_main_tab(self):
        self.tabview.add("Main")
        main_tab = self.tabview.tab("Main")
        main_tab.grid_columnconfigure(0, weight=1)
        
        # URL input
        url_label = ctk.CTkLabel(main_tab, text="URLs (one per line):", font=ctk.CTkFont(size=14, weight="bold"))
        url_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        self.url_text = ctk.CTkTextbox(main_tab, height=200)
        self.url_text.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Destination directory
        dest_frame = ctk.CTkFrame(main_tab)
        dest_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        dest_frame.grid_columnconfigure(1, weight=1)
        
        dest_label = ctk.CTkLabel(dest_frame, text="Destination Directory:", font=ctk.CTkFont(size=14))
        dest_label.grid(row=0, column=0, padx=20, pady=15)
        
        self.dest_var = tk.StringVar()
        dest_entry = ctk.CTkEntry(dest_frame, textvariable=self.dest_var, placeholder_text="Select download directory...")
        dest_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=15)
        
        dest_button = ctk.CTkButton(dest_frame, text="Browse", command=self.browse_destination, width=100)
        dest_button.grid(row=0, column=2, padx=20, pady=15)
    
    def create_general_options_tab(self):
        self.tabview.add("General")
        general_tab = self.tabview.tab("General")
        general_tab.grid_columnconfigure(0, weight=1)
        
        # Create scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(general_tab)
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        # Filename format
        filename_label = ctk.CTkLabel(scrollable_frame, text="Filename Format:", font=ctk.CTkFont(size=14))
        filename_label.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.filename_var = tk.StringVar()
        filename_entry = ctk.CTkEntry(scrollable_frame, textvariable=self.filename_var, placeholder_text="Custom filename format...")
        filename_entry.grid(row=0, column=1, sticky="ew", padx=20, pady=15)
        
        # User agent
        ua_label = ctk.CTkLabel(scrollable_frame, text="User Agent:", font=ctk.CTkFont(size=14))
        ua_label.grid(row=1, column=0, sticky="w", padx=20, pady=15)
        
        self.ua_var = tk.StringVar()
        ua_entry = ctk.CTkEntry(scrollable_frame, textvariable=self.ua_var, placeholder_text="Custom user agent string...")
        ua_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=15)
    
    def create_input_options_tab(self):
        self.tabview.add("Input")
        input_tab = self.tabview.tab("Input")
        input_tab.grid_columnconfigure(0, weight=1)
        
        scrollable_frame = ctk.CTkScrollableFrame(input_tab)
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        # Input file
        input_file_label = ctk.CTkLabel(scrollable_frame, text="Input File:", font=ctk.CTkFont(size=14))
        input_file_label.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        input_file_frame = ctk.CTkFrame(scrollable_frame)
        input_file_frame.grid(row=0, column=1, sticky="ew", padx=20, pady=15)
        input_file_frame.grid_columnconfigure(0, weight=1)
        
        self.input_file_var = tk.StringVar()
        input_file_entry = ctk.CTkEntry(input_file_frame, textvariable=self.input_file_var, placeholder_text="Select input file...")
        input_file_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        input_file_button = ctk.CTkButton(input_file_frame, text="Browse", command=self.browse_input_file, width=100)
        input_file_button.grid(row=0, column=1, padx=10, pady=10)
        
        # No input checkbox
        self.no_input_var = tk.BooleanVar()
        no_input_check = ctk.CTkCheckBox(scrollable_frame, text="Do not prompt for passwords/tokens", variable=self.no_input_var)
        no_input_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=15)
    
    def create_output_options_tab(self):
        self.tabview.add("Output")
        output_tab = self.tabview.tab("Output")
        output_tab.grid_columnconfigure(0, weight=1)
        
        scrollable_frame = ctk.CTkScrollableFrame(output_tab)
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scrollable_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Checkboxes for various output options
        self.quiet_var = tk.BooleanVar()
        quiet_check = ctk.CTkCheckBox(scrollable_frame, text="Quiet mode", variable=self.quiet_var)
        quiet_check.grid(row=0, column=0, sticky="w", padx=20, pady=10)
        
        self.verbose_var = tk.BooleanVar()
        verbose_check = ctk.CTkCheckBox(scrollable_frame, text="Verbose mode", variable=self.verbose_var)
        verbose_check.grid(row=0, column=1, sticky="w", padx=20, pady=10)
        
        self.get_urls_var = tk.BooleanVar()
        get_urls_check = ctk.CTkCheckBox(scrollable_frame, text="Print URLs instead of downloading", variable=self.get_urls_var)
        get_urls_check.grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        self.simulate_var = tk.BooleanVar()
        simulate_check = ctk.CTkCheckBox(scrollable_frame, text="Simulate (don't download)", variable=self.simulate_var)
        simulate_check.grid(row=1, column=1, sticky="w", padx=20, pady=10)

    def create_networking_tab(self):
        self.tabview.add("Networking")
        networking_tab = self.tabview.tab("Networking")
        networking_tab.grid_columnconfigure(0, weight=1)
        
        # Retries
        retries_frame = ctk.CTkFrame(networking_tab)
        retries_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        retries_frame.grid_columnconfigure(1, weight=1)
        
        retries_label = ctk.CTkLabel(retries_frame, text="Max Retries:", font=ctk.CTkFont(size=14))
        retries_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.retries_var = tk.StringVar(value="4")  # Default value
        retries_entry = ctk.CTkEntry(retries_frame, textvariable=self.retries_var, width=5, placeholder_text="4")
        retries_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Timeout
        timeout_frame = ctk.CTkFrame(networking_tab)
        timeout_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=15)
        timeout_frame.grid_columnconfigure(1, weight=1)
        
        timeout_label = ctk.CTkLabel(timeout_frame, text="HTTP Timeout (seconds):", font=ctk.CTkFont(size=14))
        timeout_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.timeout_var = tk.StringVar(value="30.0")  # Default value
        timeout_entry = ctk.CTkEntry(timeout_frame, textvariable=self.timeout_var, width=5, placeholder_text="30.0")
        timeout_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Proxy
        proxy_frame = ctk.CTkFrame(networking_tab)
        proxy_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=15)
        proxy_frame.grid_columnconfigure(1, weight=1)
        
        proxy_label = ctk.CTkLabel(proxy_frame, text="Proxy URL:", font=ctk.CTkFont(size=14))
        proxy_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.proxy_var = tk.StringVar()
        proxy_entry = ctk.CTkEntry(proxy_frame, textvariable=self.proxy_var, placeholder_text="http://proxy:port...")
        proxy_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # IP version options
        ip_frame = ctk.CTkFrame(networking_tab)
        ip_frame.grid(row=3, column=0, sticky="w", padx=20, pady=10)
        
        self.force_ipv4_var = tk.BooleanVar()
        force_ipv4_check = ctk.CTkCheckBox(ip_frame, text="Force IPv4", variable=self.force_ipv4_var)
        force_ipv4_check.grid(row=0, column=0, sticky=tk.W)
        
        self.force_ipv6_var = tk.BooleanVar()
        force_ipv6_check = ctk.CTkCheckBox(ip_frame, text="Force IPv6", variable=self.force_ipv6_var)
        force_ipv6_check.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.no_check_cert_var = tk.BooleanVar()
        no_check_cert_check = ctk.CTkCheckBox(ip_frame, text="No Certificate Check", variable=self.no_check_cert_var)
        no_check_cert_check.grid(row=0, column=2, sticky=tk.W)
    
    def create_download_tab(self):
        self.tabview.add("Download")
        download_tab = self.tabview.tab("Download")
        download_tab.grid_columnconfigure(0, weight=1)
        
        # Rate limit
        rate_frame = ctk.CTkFrame(download_tab)
        rate_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        rate_frame.grid_columnconfigure(1, weight=1)
        
        rate_label = ctk.CTkLabel(rate_frame, text="Rate Limit (e.g. 500k, 2.5M):", font=ctk.CTkFont(size=14))
        rate_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.rate_var = tk.StringVar()
        rate_entry = ctk.CTkEntry(rate_frame, textvariable=self.rate_var, width=10, placeholder_text="500k")
        rate_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Sleep between downloads
        sleep_frame = ctk.CTkFrame(download_tab)
        sleep_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=15)
        sleep_frame.grid_columnconfigure(1, weight=1)
        
        sleep_label = ctk.CTkLabel(sleep_frame, text="Sleep between downloads (seconds):", font=ctk.CTkFont(size=14))
        sleep_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.sleep_var = tk.StringVar()
        sleep_entry = ctk.CTkEntry(sleep_frame, textvariable=self.sleep_var, width=10, placeholder_text="2")
        sleep_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Various checkboxes
        check_frame = ctk.CTkFrame(download_tab)
        check_frame.grid(row=2, column=0, sticky="w", padx=20, pady=10)
        
        self.no_part_var = tk.BooleanVar()
        no_part_check = ctk.CTkCheckBox(check_frame, text="No .part files", variable=self.no_part_var)
        no_part_check.grid(row=0, column=0, sticky=tk.W)
        
        self.no_skip_var = tk.BooleanVar()
        no_skip_check = ctk.CTkCheckBox(check_frame, text="No skip (overwrite existing)", variable=self.no_skip_var)
        no_skip_check.grid(row=0, column=1, sticky=tk.W)
        
        self.no_mtime_var = tk.BooleanVar()
        no_mtime_check = ctk.CTkCheckBox(check_frame, text="No modification time", variable=self.no_mtime_var)
        no_mtime_check.grid(row=1, column=0, sticky=tk.W)
        
        self.no_download_var = tk.BooleanVar()
        no_download_check = ctk.CTkCheckBox(check_frame, text="No download (data extraction only)", variable=self.no_download_var)
        no_download_check.grid(row=1, column=1, sticky=tk.W)
    
    def create_auth_tab(self):
        self.tabview.add("Authentication")
        auth_tab = self.tabview.tab("Authentication")
        auth_tab.grid_columnconfigure(0, weight=1)
        
        # Username and password
        user_frame = ctk.CTkFrame(auth_tab)
        user_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        user_frame.grid_columnconfigure(1, weight=1)
        
        user_label = ctk.CTkLabel(user_frame, text="Username:", font=ctk.CTkFont(size=14))
        user_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.username_var = tk.StringVar()
        user_entry = ctk.CTkEntry(user_frame, textvariable=self.username_var, placeholder_text="Enter username...")
        user_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        pass_frame = ctk.CTkFrame(auth_tab)
        pass_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=15)
        pass_frame.grid_columnconfigure(1, weight=1)
        
        pass_label = ctk.CTkLabel(pass_frame, text="Password:", font=ctk.CTkFont(size=14))
        pass_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.password_var = tk.StringVar()
        pass_entry = ctk.CTkEntry(pass_frame, textvariable=self.password_var, show="*", placeholder_text="Enter password...")
        pass_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Netrc option
        self.netrc_var = tk.BooleanVar()
        netrc_check = ctk.CTkCheckBox(auth_tab, text="Enable .netrc authentication", variable=self.netrc_var)
        netrc_check.grid(row=2, column=0, sticky="w", padx=20, pady=10)
        
        # Cookies
        cookies_frame = ctk.CTkFrame(auth_tab)
        cookies_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=15)
        cookies_frame.grid_columnconfigure(1, weight=1)
        
        cookies_label = ctk.CTkLabel(cookies_frame, text="Cookies File:", font=ctk.CTkFont(size=14))
        cookies_label.grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        self.cookies_var = tk.StringVar()
        cookies_entry = ctk.CTkEntry(cookies_frame, textvariable=self.cookies_var, placeholder_text="Select cookies file...")
        cookies_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        cookies_button = ctk.CTkButton(cookies_frame, text="Browse", command=self.browse_cookies, width=100)
        cookies_button.grid(row=0, column=2, padx=20, pady=5)
    
    def create_selection_tab(self):
        self.tabview.add("Selection")
        selection_tab = self.tabview.tab("Selection")
        selection_tab.grid_columnconfigure(0, weight=1)
        
        scrollable_frame = ctk.CTkScrollableFrame(selection_tab)
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        # Filter Builder
        filter_builder_frame = ctk.CTkFrame(scrollable_frame)
        filter_builder_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        filter_builder_frame.grid_columnconfigure(1, weight=1)
        
        fb_title = ctk.CTkLabel(filter_builder_frame, text="Filter Builder", font=ctk.CTkFont(size=16, weight="bold"))
        fb_title.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))
        
        fb_type_label = ctk.CTkLabel(filter_builder_frame, text="Filter Type:", font=ctk.CTkFont(size=14))
        fb_type_label.grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        self.filter_builder_type_var = tk.StringVar(value="Extension is")
        self.filter_builder_type_combo = ctk.CTkComboBox(
            filter_builder_frame,
            variable=self.filter_builder_type_var,
            values=[
                "Extension is", "Extension is one of", "Extension is not one of",
                "Tags contain", "Tags do not contain", "Filename contains",
                "Filename does not contain", "Filename regex match", "Filename regex no match",
                "Date after", "Date before", "Date between"
            ],
            command=self.update_filter_help
        )
        self.filter_builder_type_combo.grid(row=1, column=1, sticky="ew", padx=20, pady=10)
        
        # Value entries
        fb_value_label = ctk.CTkLabel(filter_builder_frame, text="Value:", font=ctk.CTkFont(size=14))
        fb_value_label.grid(row=2, column=0, sticky="w", padx=20, pady=10)
        
        self.filter_builder_value_var = tk.StringVar()
        fb_value_entry = ctk.CTkEntry(filter_builder_frame, textvariable=self.filter_builder_value_var, placeholder_text="Enter filter value...")
        fb_value_entry.grid(row=2, column=1, sticky="ew", padx=20, pady=10)
        
        fb_value2_label = ctk.CTkLabel(filter_builder_frame, text="End Date:", font=ctk.CTkFont(size=14))
        fb_value2_label.grid(row=3, column=0, sticky="w", padx=20, pady=10)
        
        self.filter_builder_value2_var = tk.StringVar()
        fb_value2_entry = ctk.CTkEntry(filter_builder_frame, textvariable=self.filter_builder_value2_var, placeholder_text="YYYY-MM-DD (for date ranges)")
        fb_value2_entry.grid(row=3, column=1, sticky="ew", padx=20, pady=10)
        
        # Help text
        self.fb_help_var = tk.StringVar(value="Enter extension without dot (e.g., 'jpg')")
        fb_help_label = ctk.CTkLabel(filter_builder_frame, textvariable=self.fb_help_var, text_color="gray", font=ctk.CTkFont(size=12))
        fb_help_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(5, 15))
        
        fb_add_button = ctk.CTkButton(filter_builder_frame, text="Add to Filter Expression", command=self.add_to_filter_expression)
        fb_add_button.grid(row=5, column=0, columnspan=2, pady=(0, 20))
        
        # Other selection options
        row_idx = 1
        
        # Abort after N skips
        abort_label = ctk.CTkLabel(scrollable_frame, text="Abort after N skips:", font=ctk.CTkFont(size=14))
        abort_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=15)
        
        self.abort_var = tk.StringVar()
        abort_entry = ctk.CTkEntry(scrollable_frame, textvariable=self.abort_var, placeholder_text="Number", width=100)
        abort_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=15)
        row_idx += 1
        
        # File size limits
        size_frame = ctk.CTkFrame(scrollable_frame)
        size_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=20, pady=15)
        size_frame.grid_columnconfigure((1, 3), weight=1)
        
        min_size_label = ctk.CTkLabel(size_frame, text="Min Size:", font=ctk.CTkFont(size=14))
        min_size_label.grid(row=0, column=0, padx=20, pady=15)
        
        self.min_size_var = tk.StringVar()
        min_size_entry = ctk.CTkEntry(size_frame, textvariable=self.min_size_var, placeholder_text="e.g., 100KB")
        min_size_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=15)
        
        max_size_label = ctk.CTkLabel(size_frame, text="Max Size:", font=ctk.CTkFont(size=14))
        max_size_label.grid(row=0, column=2, padx=20, pady=15)
        
        self.max_size_var = tk.StringVar()
        max_size_entry = ctk.CTkEntry(size_frame, textvariable=self.max_size_var, placeholder_text="e.g., 10MB")
        max_size_entry.grid(row=0, column=3, sticky="ew", padx=20, pady=15)
        row_idx += 1
        
        # Range
        range_label = ctk.CTkLabel(scrollable_frame, text="Index Range:", font=ctk.CTkFont(size=14))
        range_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=15)
        
        self.range_var = tk.StringVar()
        range_entry = ctk.CTkEntry(scrollable_frame, textvariable=self.range_var, placeholder_text="e.g., 1-10, 1:10:2")
        range_entry.grid(row=row_idx, column=1, sticky="ew", padx=20, pady=15)
        row_idx += 1
        
        # Final Filter Expression
        filter_label = ctk.CTkLabel(scrollable_frame, text="Final Filter Expression:", font=ctk.CTkFont(size=14, weight="bold"))
        filter_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=(30, 5))
        
        self.filter_var = tk.StringVar()
        filter_entry = ctk.CTkEntry(scrollable_frame, textvariable=self.filter_var, placeholder_text="Complete filter expression...")
        filter_entry.grid(row=row_idx, column=1, sticky="ew", padx=20, pady=(30, 15))

    def create_postprocessing_tab(self):
        self.tabview.add("Post-processing")
        pp_tab = self.tabview.tab("Post-processing")
        pp_tab.grid_columnconfigure(0, weight=1)
        
        # Post-processor options
        pp_options_frame = ctk.CTkFrame(pp_tab)
        pp_options_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        
        # Various post-processing checkboxes
        self.write_metadata_var = tk.BooleanVar()
        write_metadata_check = ctk.CTkCheckBox(pp_options_frame, text="Write metadata to JSON files", variable=self.write_metadata_var)
        write_metadata_check.grid(row=0, column=0, sticky=tk.W)
        
        self.write_tags_var = tk.BooleanVar()
        write_tags_check = ctk.CTkCheckBox(pp_options_frame, text="Write image tags to text files", variable=self.write_tags_var)
        write_tags_check.grid(row=1, column=0, sticky=tk.W)
        
        self.zip_var = tk.BooleanVar()
        zip_check = ctk.CTkCheckBox(pp_options_frame, text="Store in ZIP archive", variable=self.zip_var)
        zip_check.grid(row=0, column=1, sticky=tk.W)
        
        self.cbz_var = tk.BooleanVar()
        cbz_check = ctk.CTkCheckBox(pp_options_frame, text="Store in CBZ archive", variable=self.cbz_var)
        cbz_check.grid(row=1, column=1, sticky=tk.W)
        
        # Execute command
        exec_frame = ctk.CTkFrame(pp_tab)
        exec_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=15)
        exec_frame.grid_columnconfigure(1, weight=1)
        
        exec_label = ctk.CTkLabel(exec_frame, text="Execute command for each file:", font=ctk.CTkFont(size=14))
        exec_label.grid(row=0, column=0, padx=20, pady=5)
        
        self.exec_var = tk.StringVar()
        exec_entry = ctk.CTkEntry(exec_frame, textvariable=self.exec_var, placeholder_text="Command to execute...")
        exec_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        # Execute after command
        exec_after_label = ctk.CTkLabel(exec_frame, text="Execute command after all downloads:", font=ctk.CTkFont(size=14))
        exec_after_label.grid(row=1, column=0, padx=20, pady=(5, 0))
        
        self.exec_after_var = tk.StringVar()
        exec_after_entry = ctk.CTkEntry(exec_frame, textvariable=self.exec_after_var, placeholder_text="Command to execute...")
        exec_after_entry.grid(row=1, column=1, sticky="ew", pady=5)
    
    def create_console(self):
        console_frame = ctk.CTkFrame(self.main_frame)
        console_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)
        
        console_label = ctk.CTkLabel(console_frame, text="Output Console", font=ctk.CTkFont(size=16, weight="bold"))
        console_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Use regular tkinter scrolledtext for console as CustomTkinter doesn't have a direct equivalent
        self.console = scrolledtext.ScrolledText(
            console_frame, 
            height=10, 
            bg="#212121", 
            fg="#ffffff", 
            insertbackground="#ffffff",
            font=("Consolas", 10)
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.console.config(state=tk.DISABLED)
    
    def browse_destination(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dest_var.set(directory)
    
    def browse_input_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.input_file_var.set(filename)
    
    def browse_cookies(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.cookies_var.set(filename)

    def add_to_filter_expression(self):
        filter_type = self.filter_builder_type_var.get()
        filter_value_str = self.filter_builder_value_var.get().strip()

        if not filter_value_str:
            self.log_to_console("Filter builder: Value cannot be empty.")
            return

        new_filter_condition = ""
        
        if filter_type == "Extension is":
            new_filter_condition = f"extension == '{filter_value_str}'"
            
        elif filter_type == "Extension is one of":
            values = [f"'{val.strip()}'" for val in filter_value_str.split(',') if val.strip()]
            if not values:
                self.log_to_console("Filter builder: No valid values provided.")
                return
            new_filter_condition = f"extension in ({', '.join(values)})"
            
        elif filter_type == "Extension is not one of":
            values = [f"'{val.strip()}'" for val in filter_value_str.split(',') if val.strip()]
            if not values:
                self.log_to_console("Filter builder: No valid values provided.")
                return
            new_filter_condition = f"extension not in ({', '.join(values)})"
            
        elif filter_type == "Tags contain":
            tags = [f"'''{tag.strip()}'''" for tag in filter_value_str.split(',') if tag.strip()]
            if not tags:
                self.log_to_console("Filter builder: No valid tags provided.")
                return
            new_filter_condition = f"contains(tags, ({', '.join(tags)}))"
            
        elif filter_type == "Tags do not contain":
            tags = [f"'''{tag.strip()}'''" for tag in filter_value_str.split(',') if tag.strip()]
            if not tags:
                self.log_to_console("Filter builder: No valid tags provided.")
                return
            new_filter_condition = f"not contains(tags, ({', '.join(tags)}))"
            
        elif filter_type == "Filename contains":
            new_filter_condition = f"'{filter_value_str.lower()}' in filename.lower()"
            
        elif filter_type == "Filename does not contain":
            new_filter_condition = f"'{filter_value_str.lower()}' not in filename.lower()"
            
        elif filter_type == "Filename regex match":
            new_filter_condition = f"re.search(r'{filter_value_str}', filename)"
            
        elif filter_type == "Filename regex no match":
            new_filter_condition = f"not re.search(r'{filter_value_str}', filename)"
            
        elif filter_type == "Date after":
            try:
                # Validate date format
                parts = filter_value_str.split('-')
                if len(parts) != 3:
                    raise ValueError("Invalid date format")
                year, month, day = map(int, parts)
                new_filter_condition = f"date >= datetime({year}, {month}, {day})"
            except ValueError:
                self.log_to_console("Filter builder: Invalid date format. Use YYYY-MM-DD.")
                return
                
        elif filter_type == "Date before":
            try:
                parts = filter_value_str.split('-')
                if len(parts) != 3:
                    raise ValueError("Invalid date format")
                year, month, day = map(int, parts)
                new_filter_condition = f"date < datetime({year}, {month}, {day})"
            except ValueError:
                self.log_to_console("Filter builder: Invalid date format. Use YYYY-MM-DD.")
                return
                
        elif filter_type == "Date between":
            filter_value2_str = self.filter_builder_value2_var.get().strip()
            if not filter_value2_str:
                self.log_to_console("Filter builder: End date is required for date range.")
                return
            try:
                parts1 = filter_value_str.split('-')
                parts2 = filter_value2_str.split('-')
                if len(parts1) != 3 or len(parts2) != 3:
                    raise ValueError("Invalid date format")
                year1, month1, day1 = map(int, parts1)
                year2, month2, day2 = map(int, parts2)
                new_filter_condition = f"datetime({year1}, {month1}, {day1}) <= date < datetime({year2}, {month2}, {day2})"
            except ValueError:
                self.log_to_console("Filter builder: Invalid date format. Use YYYY-MM-DD for both dates.")
                return
        
        if not new_filter_condition:
            self.log_to_console("Filter builder: Could not generate filter condition.")
            return

        current_filter_expr = self.filter_var.get().strip()
        if current_filter_expr:
            self.filter_var.set(f"{current_filter_expr} and {new_filter_condition}")
        else:
            self.filter_var.set(new_filter_condition)
        
        self.log_to_console(f"Added to filter: {new_filter_condition}")
        self.filter_builder_value_var.set("") # Clear the value input
        self.filter_builder_value2_var.set("") # Clear the second value input

    def update_filter_help(self, choice=None):
        filter_type = self.filter_builder_type_var.get()
        help_texts = {
            "Extension is": "Enter extension without dot (e.g., 'jpg')",
            "Extension is one of": "Enter extensions separated by commas (e.g., 'jpg,png,gif')",
            "Extension is not one of": "Enter extensions separated by commas (e.g., 'jpg,png,gif')",
            "Tags contain": "Enter tags separated by commas (e.g., 'tag1,tag2'). Uses triple quotes for apostrophes.",
            "Tags do not contain": "Enter tags separated by commas (e.g., 'tag1,tag2'). Uses triple quotes for apostrophes.",
            "Filename contains": "Enter text that should be in filename (case insensitive)",
            "Filename does not contain": "Enter text that should NOT be in filename (case insensitive)",
            "Filename regex match": "Enter regex pattern (e.g., '(?i)stills|mainvid' for case insensitive)",
            "Filename regex no match": "Enter regex pattern to exclude",
            "Date after": "Enter date in YYYY-MM-DD format (e.g., '2020-01-01')",
            "Date before": "Enter date in YYYY-MM-DD format (e.g., '2020-12-31')",
            "Date between": "Enter start date, end date below (both in YYYY-MM-DD format)"
        }
        self.fb_help_var.set(help_texts.get(filter_type, ""))

    def log_to_console(self, text):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
    
    def log_to_console_if_exists(self, text):
        """Helper method to log to console only if it exists (for early initialization)."""
        if hasattr(self, 'console'):
            self.log_to_console(text)
        else:
            print(text)  # Fallback to print during initialization

    def build_command(self):
        # Use the found or downloaded gallery-dl path
        command = [self.gallery_dl_path or "gallery-dl"]
        
        # Add URLs
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        urls = [url for url in urls if url]  # Filter out empty lines
        
        # Add options based on UI selections
        if self.dest_var.get():
            command.extend(["-d", self.dest_var.get()])
        
        if self.filename_var.get():
            command.extend(["-f", self.filename_var.get()])
        
        if self.ua_var.get():
            command.extend(["--user-agent", self.ua_var.get()])
        
        if self.input_file_var.get():
            command.extend(["-i", self.input_file_var.get()])
        
        if self.no_input_var.get():
            command.append("--no-input")
        
        if self.quiet_var.get():
            command.append("-q")
        
        if self.verbose_var.get():
            command.append("-v")
        
        if self.get_urls_var.get():
            command.append("-g")
        
        if self.simulate_var.get():
            command.append("-s")
        
        if self.retries_var.get():
            command.extend(["-R", self.retries_var.get()])
        
        if self.timeout_var.get():
            command.extend(["--http-timeout", self.timeout_var.get()])
        
        if self.proxy_var.get():
            command.extend(["--proxy", self.proxy_var.get()])
        
        if self.force_ipv4_var.get():
            command.append("-4")
        
        if self.force_ipv6_var.get():
            command.append("-6")
        
        if self.no_check_cert_var.get():
            command.append("--no-check-certificate")
        
        if self.rate_var.get():
            command.extend(["-r", self.rate_var.get()])
        
        if self.sleep_var.get():
            command.extend(["--sleep", self.sleep_var.get()])
        
        if self.no_part_var.get():
            command.append("--no-part")
        
        if self.no_skip_var.get():
            command.append("--no-skip")
        
        if self.no_mtime_var.get():
            command.append("--no-mtime")
        
        if self.no_download_var.get():
            command.append("--no-download")
        
        if self.username_var.get():
            command.extend(["-u", self.username_var.get()])
        
        if self.password_var.get():
            command.extend(["-p", self.password_var.get()])
        
        if self.netrc_var.get():
            command.append("--netrc")
        
        if self.cookies_var.get():
            command.extend(["-C", self.cookies_var.get()])
        
        if self.abort_var.get():
            command.extend(["-A", self.abort_var.get()])
        
        if self.min_size_var.get():
            command.extend(["--filesize-min", self.min_size_var.get()])
        
        if self.max_size_var.get():
            command.extend(["--filesize-max", self.max_size_var.get()])
        
        if self.range_var.get():
            command.extend(["--range", self.range_var.get()])
        
        if self.filter_var.get():
            command.extend(["--filter", self.filter_var.get()])
        
        if self.write_metadata_var.get():
            command.append("--write-metadata")
        
        if self.write_tags_var.get():
            command.append("--write-tags")
        
        if self.zip_var.get():
            command.append("--zip")
        
        if self.cbz_var.get():
            command.append("--cbz")
        
        if self.exec_var.get():
            command.extend(["--exec", self.exec_var.get()])
        
        if self.exec_after_var.get():
            command.extend(["--exec-after", self.exec_after_var.get()])
        
        # Add URLs at the end
        command.extend(urls)
        
        return command
    
    def run_gallery_dl(self):
        if not self.gallery_dl_path:
            messagebox.showerror(
                "Gallery-DL Not Found", 
                "Gallery-DL executable not found. Please download it first."
            )
            return
        
        command = self.build_command()
        
        self.log_to_console("Running command: " + " ".join(command))
        
        def run_process():
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    self.log_to_console(line.strip())
                
                process.wait()
                self.log_to_console(f"Process completed with return code {process.returncode}")
            
            except Exception as e:
                self.log_to_console(f"Error: {str(e)}")
        
        # Run the process in a separate thread to avoid blocking the UI
        threading.Thread(target=run_process, daemon=True).start()

def main():
    root = ctk.CTk()
    app = GalleryDLUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
