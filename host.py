import os
import dbus

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QListWidgetItem
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QComboBox

from test_automation.UI.Backend_lib.Linux.filewatcher import BluezLogger
# from test_automation.UI.Backend_lib.Linux.bluez_utils import BluezLogger
from test_automation.UI.UI_lib.controller_lib import Controller
from test_automation.UI.logger import Logger
from test_automation.UI.Backend_lib.Linux.a2dp_profile import A2DPManager
from test_automation.UI.Backend_lib.Linux.opp_profile import OPPManager
from test_automation.UI.Backend_lib.Linux.daemons import BluezServices


class Controller:
    """
    Represents the local Bluetooth controller.

    Stores HCI version, manufacturer details, address, and link policies.
    """

    def __init__(self):
        self.name = None
        self.bd_address = None
        self.link_mode = None
        self.link_policy = None
        self.hci_version = None
        self.lmp_version = None
        self.manufacturer = None


class TestApplication(QWidget):
    """
    Main GUI class for the Bluetooth Test Host.

    Handles Bluetooth discovery, pairing, connection (BR/EDR & LE), A2DP streaming,
    and media control operations using BlueZ and PulseAudio.
    """

    def __init__(self, interface=None, log_path=None, back_callback=None):
        """
        Initialize the TestApplication widget.

        Args:
            interface (str): Bluetooth adapter interface (e.g., hci0).
            log_path (str): Path to the log file for capturing events.
            back_callback (callable): Optional callback to trigger on back action.

        returns:
            None
        """
        super().__init__()
        self.log = Logger("UI")
        self.log_path = log_path
        self.bluez_logger = BluezLogger(self.log_path)
        self.interface = interface
        self.discovery_active = False
        self.a2dp_manager = A2DPManager(interface=self.interface)
        self.opp_manager = OPPManager()
        self.device_address_source = None
        self.device_address_sink = None

        self.back_callback = back_callback
        self.controller = Controller()
        self.test_application_clicked()
        self.bluetooth_device_manager = BluezServices(interface=self.interface)
        #self.profiles_list_widget.itemClicked.connect(self.on_profile_item_clicked)

        # self.defer_log_start()

    def defer_log_start(self):
        QTimer.singleShot(100, self.start_logs)

    def start_logs(self):
        self.bluez_logger.start_bluetoothd_logs(self.bluetoothd_log_text_browser)
        self.bluez_logger.start_pulseaudio_logs(self.pulseaudio_log_text_browser)
        # self.bluez_logger.start_dump_logs(
        #   interface=self.interface,
        #  log_text_browser=self.hci_dump_log_text_browser)

    def set_discoverable_on(self):
        """
        Set the local Bluetooth device to discoverable mode.
        Starts a timeout if specified in the UI input.

        args: None
        returns: None
        """
        print("Discoverable is set to ON")
        self.set_discoverable_on_button.setEnabled(False)
        self.set_discoverable_off_button.setEnabled(True)
        self.bluetooth_device_manager.set_discoverable_on()
        timeout = int(self.discoverable_timeout_input.text())
        if timeout > 0:
            self.discoverable_timeout_timer = QTimer()
            self.discoverable_timeout_timer.timeout.connect(self.set_discoverable_off)
            self.discoverable_timeout_timer.start(timeout * 1000)

    def set_discoverable_off(self):
        """
        Disable discoverable mode on the Bluetooth adapter.
        Stops any active discoverable timer.

        args: None
        returns: None
        """
        print("Discoverable is set to OFF")
        self.set_discoverable_on_button.setEnabled(True)
        self.set_discoverable_off_button.setEnabled(False)
        self.bluetooth_device_manager.set_discoverable_off()
        if hasattr(self, 'discoverable_timeout_timer'):
            self.discoverable_timeout_timer.stop()

    def inquiry(self):
        """Function for Inquiry"""

    def set_discovery_on(self):
        """
        Start device discovery.
        If a timeout is specified, stops discovery and shows results after the timeout.

        args: None
        returns: None
        """
        print("Discovery has started")
        self.inquiry_timeout = int(self.inquiry_timeout_input.text()) * 1000
        if self.inquiry_timeout == 0:
            self.set_discovery_on_button.setEnabled(False)
            self.set_discovery_off_button.setEnabled(True)
            self.bluetooth_device_manager.start_discovery()
        else:
            self.timer = QTimer()
            self.timer.timeout.connect(self.show_discovery_table_timeout)
            self.timer.timeout.connect(lambda: self.set_discovery_off_button.setEnabled(False))
            self.timer.start(self.inquiry_timeout)
            self.set_discovery_on_button.setEnabled(False)
            self.set_discovery_off_button.setEnabled(True)
            self.bluetooth_device_manager.start_discovery()

    def show_discovery_table_timeout(self):
        """Function to show the discovery table when timeout is over

        args: None
        returns: None
        """
        self.timer.stop()
        self.bluetooth_device_manager.stop_discovery()
        self.show_discovery_table()

    def set_discovery_off(self):
        """Function for Stop Discovery

        args: None
        returns: None
        """

        print("Discovery has stopped")
        self.set_discovery_off_button.setEnabled(False)
        self.timer = QTimer()
        if self.inquiry_timeout == 0:
            self.bluetooth_device_manager.stop_discovery()
            self.show_discovery_table()
        else:
            self.timer.stop()
            self.bluetooth_device_manager.stop_discovery()
            self.show_discovery_table()
            self.set_discovery_off_button.setEnabled(False)

    def show_discovery_table(self):
        """
        Display discovered devices in a table with options to pair or connect (BR/EDR, LE).
        """
        self.timer.stop()
        bold_font = QFont()
        bold_font.setBold(True)
        bus = dbus.SystemBus()
        om = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        devices = [path for path, interfaces in objects.items() if "org.bluez.Device1" in interfaces]
        self.table_widget = QTableWidget(len(devices), 3)
        self.table_widget.setHorizontalHeaderLabels(["DEVICE NAME", "BD_ADDR", "PROCEDURES"])
        self.table_widget.setFont(bold_font)
        self.table_widget.setFixedSize(475, 220)

        for i, device_path in enumerate(devices):
            device = dbus.Interface(bus.get_object("org.bluez", device_path), dbus_interface="org.bluez.Device1")
            device_props = dbus.Interface(bus.get_object("org.bluez", device_path),
                                          dbus_interface="org.freedesktop.DBus.Properties")
            device_address = device_props.Get("org.bluez.Device1", "Address")
            device_name = device_props.Get("org.bluez.Device1", "Alias")
            self.table_widget.setItem(i, 0, QTableWidgetItem(device_name))
            self.table_widget.setItem(i, 1, QTableWidgetItem(device_address))
            self.table_widget.horizontalHeader().setStretchLastSection(True)
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            pair_button = QPushButton("PAIR")
            pair_button.setFont(bold_font)
            pair_button.setStyleSheet("color:green")
            pair_button.setMinimumSize(30, 20)
            button_layout.addWidget(pair_button)

            br_edr_connect_button = QPushButton("BR_EDR_CONNECT")
            br_edr_connect_button.setFont(bold_font)
            br_edr_connect_button.setStyleSheet("color:green")
            br_edr_connect_button.setMinimumSize(30, 20)
            button_layout.addWidget(br_edr_connect_button)

            le_connect_button = QPushButton("LE_CONNECT")
            le_connect_button.setFont(bold_font)
            le_connect_button.setStyleSheet("color:green")
            le_connect_button.setMinimumSize(30, 20)
            button_layout.addWidget(le_connect_button)

            button_widget.setLayout(button_layout)
            self.table_widget.setCellWidget(i, 2, button_widget)
            self.gap_methods_layout.addWidget(self.table_widget)
            pair_button.clicked.connect(
                lambda checked, address=device_address: self.handle_device_action('pair', address))
            br_edr_connect_button.clicked.connect(
                lambda checked, address=device_address: self.handle_device_action('br_edr_connect', address))
            le_connect_button.clicked.connect(
                lambda checked, address=device_address: self.handle_device_action('le_connect', address))
        self.table_widget.show()
        self.set_discovery_off_button.setEnabled(False)

    def handle_device_action(self, action, address):
        """
        Handle user-selected action (pair/BR-EDR/LE connect) for a device.

        Args:
            action (str): Action to perform.
            address (str): Bluetooth device address.

        returns:
            None
        """

        self.device_address = address
        if action == 'pair':
            self.pair(address)
        elif action == 'br_edr_connect':
            self.br_edr_connect(address)
        elif action == 'le_connect':
            self.le_connect(address)

    def pair(self, device_address):
        """
        Attempt to pair with the given Bluetooth device.

        Args:
            device_address (str): Bluetooth MAC address.
        """
        print(f"Attempting to pair with {device_address}")

        # Check if already paired
        if self.bluetooth_device_manager.is_device_paired(device_address):
            QMessageBox.information(self, "Already Paired", f"{device_address} is already paired.")
            return

        # This will block until confirmation is handled
        success = self.bluetooth_device_manager.pair(device_address)

        if success:
            QMessageBox.information(self, "Pairing Result", f"Pairing with {device_address} was successful.")
            self.add_device(device_address)
        else:
            QMessageBox.critical(self, "Pairing Failed", f"Pairing with {device_address} failed.")

    def br_edr_connect(self, device_address):
        """
        Connect to a device using BR/EDR.

        Args:
            device_address (str): Bluetooth MAC address.
        returns:
            None
        """

        print(f"Attempting BR/EDR connect with {device_address}")
        success = self.bluetooth_device_manager.br_edr_connect(device_address)
        if success:
            QMessageBox.information(self, "Connection Result", f"Connection with {device_address} was successful.")
            self.add_device(device_address)
        else:
            QMessageBox.critical(self, "Connection Failed", f"Connection with {device_address} failed.")

    def le_connect(self, device_address):
        """
        Connect to a device using LE (Low Energy).

        Args:
            device_address (str): Bluetooth MAC address.
        returns:
            None
        """

        print("LE_Connect is ongoing ")
        self.bluetooth_device_manager.le_connect(device_address)

    def refresh(self):
        """
        Refresh and clear the device discovery table.

        args: None
        returns: None
        """

        print("Refresh Button is pressed")
        if hasattr(self, 'table_widget') and self.table_widget:
            self.gap_methods_layout.removeWidget(self.table_widget)
            self.table_widget.deleteLater()
            self.table_widget = None
            self.inquiry_timeout_input.setText("0")
            self.refresh_button.setEnabled(False)
            self.set_discovery_on_button.setEnabled(True)
            self.set_discovery_off_button.setEnabled(False)
            self.refresh_button.setEnabled(True)

    def refresh_discoverable(self):
        """
        Reset discoverable timeout input to default (0).

        args: None
        returns: None
        """
        print("Discoverable refresh button is pressed")
        self.discoverable_timeout_input.setText("0")

    def start_streaming(self,device_name):
        """
        Start A2DP streaming to a selected Bluetooth sink device.
        Validates file and device selection.

        args:None
        returns: None

        """

        audio_path = self.audio_location_input.text().strip()
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "Invalid Audio File", "Please select a valid audio file to stream.")
            return

        # Ensure that the correct sink device is selected
        selected_index = self.device_selector.currentIndex()
        self.device_address_source = self.device_selector.itemData(selected_index)

        print(f"Selected device address for streaming: {self.device_address_source}")

        if not self.device_address_source:
            QMessageBox.warning(self, "No Device", "Please select a Bluetooth sink device to stream.")
            return

        print(f"A2DP streaming started with file: {audio_path}")

        self.start_streaming_button.setEnabled(False)
        self.stop_streaming_button.setEnabled(True)

        # Create BluetoothDeviceManager instance and start streaming
        success = self.a2dp_manager.start_streaming(self.device_address_source, audio_path)

        if not success:
            QMessageBox.critical(self, "Streaming Failed", "Failed to start streaming.")
            self.start_streaming_button.setEnabled(True)
            self.stop_streaming_button.setEnabled(False)

    def stop_streaming(self):
        """
        Stop active A2DP streaming session.

        args: None
        returns: None
        """
        print("A2DP streaming stopped")
        self.start_streaming_button.setEnabled(True)
        self.stop_streaming_button.setEnabled(False)

        self.a2dp_manager.stop_streaming()

        if hasattr(self, 'streaming_timer'):
            self.streaming_timer.stop()

    def play(self):
        """
        Send media play command to sink device.

        args: None
        returns: None
        """
        print("Play button has been pressed")
        print(f"device_address_sink = {self.device_address_sink}")  # Debugging line
        if self.device_address_sink:
            self.a2dp_manager.play(self.device_address_sink)
        else:
            QMessageBox.warning(self, "No Device", "Please select a sink device for media control.")

    def pause(self):
        """
        Send media pause command to sink device.

        args : None
        returns: None
        """
        print("Pause button has been pressed")
        print(f"device_address_sink = {self.device_address_sink}")
        if self.device_address_sink:
            self.a2dp_manager.pause(self.device_address_sink)
        else:
            QMessageBox.warning(self, "No Device", "Please select a sink device for media control.")

    def next(self):
        """
        Send media next track command to sink device.

        args : None
        returns: None
        """

        print(f"Next button has been pressed. Device address: {self.device_address_sink}")  # Debugging line
        if self.device_address_sink:
            self.a2dp_manager.next(self.device_address_sink)
        else:
            QMessageBox.warning(self, "No Device", "Please select a sink device for media control.")

    def previous(self):
        """
        Handle media control action: Previous track.

        args: None
        returns: None
        """
        print(f"Previous button has been pressed. Device address: {self.device_address_sink}")  # Debugging line
        if self.device_address_sink:
            self.a2dp_manager.previous(self.device_address_sink)
        else:
            QMessageBox.warning(self, "No Device", "Please select a sink device for media control.")

    def rewind(self):
        """Handle media control action: Rewind track.

        args: None
        returns: None
        """
        print(f"Rewind button has been pressed. Device address: {self.device_address_sink}")  # Debugging line
        if self.device_address_sink:
            self.a2dp_manager.rewind(self.device_address_sink)
        else:
            QMessageBox.warning(self, "No Device", "Please select a sink device for media control.")

    def refresh_a2dp_sink_devices(self):
        """Refresh the list of connected A2DP source devices for sink control.

        args: None
        returns: None
        """
        self.device_selector_sink.clear()
        connected_sources = self.a2dp_manager.get_connected_a2dp_source_devices()
        for address, name in connected_sources.items():
            self.device_selector_sink.addItem(f"{name} ({address})", address)

    def browse_audio_file(self):
        """Open a file dialog for selecting an audio file.

        args: None
        returns: None
        """
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select Audio File", "",
                                                   "Audio Files (*.mp3 *.wav *.ogg *.flac);;All Files (*)")
        if file_path:
            self.audio_location_input.setText(file_path)

    def build_a2dp_source_tab(self, device_name):
        """
        Build UI for A2DP Source streaming for a specific device.
        """
        layout = QVBoxLayout()
        bold_font = QFont()
        bold_font.setBold(True)

        label = QLabel(f"A2DP Source: {device_name}")
        label.setFont(bold_font)
        layout.addWidget(label)

        # Audio file selection
        audio_layout = QHBoxLayout()
        audio_label = QLabel("Audio Location:")
        audio_label.setFont(bold_font)
        audio_label.setStyleSheet("color:white;")
        audio_layout.addWidget(audio_label)
        self.audio_location_input = QLineEdit()
        self.audio_location_input.setReadOnly(True)
        audio_layout.addWidget(self.audio_location_input)
        self.browse_audio_button = QPushButton("Browse")
        self.browse_audio_button.setFont(bold_font)
        self.browse_audio_button.clicked.connect(self.browse_audio_file)
        audio_layout.addWidget(self.browse_audio_button)
        layout.addLayout(audio_layout)

        # A2DP streaming control
        self.start_stream_button = QPushButton("Start Streaming")
        self.start_stream_button.setFont(bold_font)
        self.start_stream_button.setStyleSheet("color:green;")
        self.start_stream_button.clicked.connect(lambda: self.start_streaming(device_name))
        layout.addWidget(self.start_stream_button)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def build_a2dp_sink_tab(self, device_name):
        """
        Build UI for A2DP Sink media controls for a specific connected source device.
        """
        bold_font = QFont()
        bold_font.setBold(True)
        layout = QVBoxLayout()

        label = QLabel(f"A2DP Sink (Media Control) for: {device_name}")
        label.setFont(bold_font)
        layout.addWidget(label)

        # Save device address (assuming you can fetch it from name via helper, or modify to pass address directly)
        #self.device_address_sink = self.resolve_device_address(device_name)  # Implement this helper
        print(f"Controlling A2DP sink for: {device_name} )")

        # Media control buttons
        control_label = QLabel("Media Control:")
        control_label.setFont(bold_font)
        control_label.setStyleSheet("color:white;")
        layout.addWidget(control_label)

        control_buttons = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.play_button.setFont(bold_font)
        self.play_button.clicked.connect(self.play)
        control_buttons.addWidget(self.play_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setFont(bold_font)
        self.pause_button.clicked.connect(self.pause)
        control_buttons.addWidget(self.pause_button)

        self.next_button = QPushButton("Next")
        self.next_button.setFont(bold_font)
        self.next_button.clicked.connect(self.next)
        control_buttons.addWidget(self.next_button)

        self.previous_button = QPushButton("Previous")
        self.previous_button.setFont(bold_font)
        self.previous_button.clicked.connect(self.previous)
        control_buttons.addWidget(self.previous_button)

        self.rewind_button = QPushButton("Rewind")
        self.rewind_button.setFont(bold_font)
        self.rewind_button.clicked.connect(self.rewind)
        control_buttons.addWidget(self.rewind_button)

        layout.addLayout(control_buttons)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setStyleSheet("background-color:light blue;")
        return widget


    def browse_opp_file(self):
        """
        Open a file dialog to select a file to send via OPP.

        args: None
        returns: None
        """

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            None,
            "Select File to Send via OPP",
            "",
            "All Files (*)"
        )
        if file_path:
            self.opp_location_input.setText(file_path)

    def send_file(self):
        """
        Send a selected file to a remote device using OPP.

        args: None
        returns: None
        """

        file_path = self.opp_location_input.text()
        device_index = self.device_selector.currentIndex()
        device_address = self.device_selector.itemData(device_index)

        if not file_path or not device_address:
            QMessageBox.warning(None, "OPP", "Please select a device and a file.")
            return

        self.send_file_button.setEnabled(False)
        self.send_file_button.setText("Sending...")

        try:
            success = self.opp_manager.send_file_via_obex(device_address, file_path)
        except Exception as e:
            success = False
            print(f"UI error: {e}")

        self.send_file_button.setEnabled(True)
        self.send_file_button.setText("Send File")

        if success is True:
            QMessageBox.information(None, "OPP", "File sent successfully!")
        else:
            QMessageBox.warning(None, "OPP",
                                "Notification has been sent to the remote device, accept it to receive the object")

    def receive_file(self):
        """
        Start OPP receiver to receive files from a remote device.

        args: None
        returns: None
        """

        success = self.opp_manager.start_opp_receiver()
        QMessageBox.information(None, "OPP", "Ready to receive files..." if success else "Failed to start receiver.")

    def test_application_clicked(self):
        """
           Create and display the main testing application GUI.

           This interface consists of:
           - A profile selection list
           - Bluetooth controller details
           - A text browser showing methods related to selected profile
           - Three log viewers: Bluetoothd, PulseAudio, and HCI Dump
           - A back button to return to the previous window

           args: None
           returns: None
           """

        # Create the main grid
        self.main_grid_layout = QGridLayout()

        # Grid 1 Up : List of Profiles
        bold_font = QFont()
        bold_font.setBold(True)
        self.profiles_list_widget = QListWidget()
        self.profiles_list_label = QLabel("List of Profiles:")
        self.profiles_list_label.setFont(bold_font)
        self.profiles_list_label.setStyleSheet("color:black")
        self.main_grid_layout.addWidget(self.profiles_list_label, 0, 0)
        self.profiles_list_widget.addItem("GAP")
        # profiles_list_widget.addItem("A2DP")
        # profiles_list_widget.addItem("HFP")
        # profiles_list_widget.addItem("OPP")
        # profiles_list_widget.addItem("GATT")
        self.profiles_list_widget.setFont(bold_font)
        self.profiles_list_widget.setStyleSheet("border: 3px solid black;" "color: black;" "background: transparent;")
        self.profiles_list_widget.itemSelectionChanged.connect(self.profile_selected)
        self.profiles_list_widget.setFixedWidth(350)
        self.main_grid_layout.addWidget(self.profiles_list_widget, 1, 0, 2, 2)

        # Grid 1 Down : Controller Details
        controller_details_widget = QWidget()
        controller_details_layout = QVBoxLayout()
        controller_details_widget.setStyleSheet("color: blue;")
        controller_details_widget.setFont(bold_font)
        controller_details_widget.setStyleSheet("border: 2px solid black;" "color: black;" "background: transparent;")
        self.main_grid_layout.addWidget(controller_details_widget, 3, 0, 8, 2)
        controller_details_layout.setContentsMargins(0, 0, 0, 0)
        controller_details_layout.setSpacing(0)

        self.bluez_logger.get_controller_details(interface=self.interface)

        self.controller.name = self.bluez_logger.name
        self.controller.bd_address = self.bluez_logger.bd_address
        self.controller.link_policy = self.bluez_logger.link_policy
        self.controller.lmp_version = self.bluez_logger.lmp_version
        self.controller.link_mode = self.bluez_logger.link_mode
        self.controller.hci_version = self.bluez_logger.hci_version
        self.controller.manufacturer = self.bluez_logger.manufacturer

        controller_details_label = QLabel("Controller Details:")

        controller_details_label.setFont(bold_font)
        controller_details_layout.addWidget(controller_details_label)

        # Controller Name
        controller_name_layout = QHBoxLayout()
        controller_name_label = QLabel("Controller Name:")
        controller_name_label.setFont(bold_font)
        controller_name_layout.addWidget(controller_name_label)
        controller_name_text = QLabel(self.bluez_logger.name)
        controller_name_layout.addWidget(controller_name_text)
        controller_details_layout.addLayout(controller_name_layout)

        # Controller Address
        controller_address_layout = QHBoxLayout()
        controller_address_label = QLabel("Controller Address:")
        controller_address_label.setFont(bold_font)
        controller_address_layout.addWidget(controller_address_label)
        controller_address_text = QLabel(self.bluez_logger.bd_address)
        controller_address_layout.addWidget(controller_address_text)
        controller_details_layout.addLayout(controller_address_layout)

        # Link Mode
        controller_link_mode_layout = QHBoxLayout()
        controller_link_mode_label = QLabel("Link Mode:")
        controller_link_mode_label.setFont(bold_font)
        controller_link_mode_layout.addWidget(controller_link_mode_label)
        controller_link_mode_text = QLabel(self.bluez_logger.link_mode)
        controller_link_mode_layout.addWidget(controller_link_mode_text)
        controller_details_layout.addLayout(controller_link_mode_layout)

        # Link Policy
        controller_link_policy_layout = QHBoxLayout()
        controller_link_policy_label = QLabel("Link Policy:")
        controller_link_policy_label.setFont(bold_font)
        controller_link_policy_layout.addWidget(controller_link_policy_label)
        controller_link_policy_text = QLabel(self.bluez_logger.link_policy)
        controller_link_policy_layout.addWidget(controller_link_policy_text)
        controller_details_layout.addLayout(controller_link_policy_layout)

        # HCI Version
        controller_hci_version_layout = QHBoxLayout()
        controller_hci_version_label = QLabel("HCI Version:")
        controller_hci_version_label.setFont(bold_font)
        controller_hci_version_layout.addWidget(controller_hci_version_label)
        controller_hci_version_text = QLabel(self.bluez_logger.hci_version)
        controller_hci_version_layout.addWidget(controller_hci_version_text)
        controller_details_layout.addLayout(controller_hci_version_layout)

        # LMP Version
        controller_lmp_version_layout = QHBoxLayout()
        controller_lmp_version_label = QLabel("LMP Version:")
        controller_lmp_version_label.setFont(bold_font)
        controller_lmp_version_layout.addWidget(controller_lmp_version_label)
        controller_lmp_version_text = QLabel(self.bluez_logger.lmp_version)
        controller_lmp_version_layout.addWidget(controller_lmp_version_text)
        controller_details_layout.addLayout(controller_lmp_version_layout)

        # Manufacturer
        controller_manufacturer_layout = QHBoxLayout()
        controller_manufacturer_label = QLabel("Manufacturer:")
        controller_manufacturer_label.setFont(bold_font)
        controller_manufacturer_label.setFixedWidth(350)
        controller_manufacturer_layout.addWidget(controller_manufacturer_label)
        controller_manufacturer_text = QLabel(self.bluez_logger.manufacturer)
        controller_manufacturer_layout.addWidget(controller_manufacturer_text)
        controller_details_layout.addLayout(controller_manufacturer_layout)

        # Setting the controller details widget with fixedwidth being mentioned
        controller_details_widget.setLayout(controller_details_layout)
        controller_details_widget.setFixedWidth(350)

        # Grid2: Profile description
        profile_description_label = QLabel("Profile Methods or Procedures:")
        profile_description_label.setFont(bold_font)
        profile_description_label.setStyleSheet("color: black;")

        self.main_grid_layout.addWidget(profile_description_label, 0, 2)
        self.profile_description_text_browser = QTextBrowser()
        self.main_grid_layout.addWidget(self.profile_description_text_browser, 1, 2, 10, 2)
        self.profile_description_text_browser.setStyleSheet(
            "background: transparent;color:black;border: 2px solid black;")
        self.profile_description_text_browser.setFixedWidth(500)

        # Grid3: HCI Dump Logs
        dump_logs_label = QLabel("Dump Logs:")
        dump_logs_label.setFont(bold_font)
        dump_logs_label.setStyleSheet("color: black;")
        self.main_grid_layout.addWidget(dump_logs_label, 0, 4)
        self.dump_logs_text_browser = QTabWidget()
        self.main_grid_layout.addWidget(self.dump_logs_text_browser, 1, 4, 10, 2)
        self.dump_logs_text_browser.setStyleSheet("border: 2px solid black;color: black; background-color: lightblue;")
        self.dump_logs_text_browser.setFixedWidth(400)

        self.bluetoothd_log_text_browser = QTextEdit()
        self.bluetoothd_log_text_browser.setFont(bold_font)
        self.bluetoothd_log_text_browser.setMinimumWidth(30)
        self.bluetoothd_log_text_browser.setReadOnly(True)

        self.pulseaudio_log_text_browser = QTextEdit()
        self.pulseaudio_log_text_browser.setFont(bold_font)
        self.pulseaudio_log_text_browser.setMinimumWidth(30)
        self.pulseaudio_log_text_browser.setReadOnly(True)

        self.hci_dump_log_text_browser = QTextEdit()
        self.hci_dump_log_text_browser.setFont(bold_font)
        self.hci_dump_log_text_browser.setMinimumWidth(30)
        self.hci_dump_log_text_browser.setReadOnly(True)

        self.dump_logs_text_browser.addTab(self.bluetoothd_log_text_browser, "Bluetoothd_Logs")
        self.dump_logs_text_browser.addTab(self.pulseaudio_log_text_browser, "Pulseaudio_Logs")
        self.dump_logs_text_browser.addTab(self.hci_dump_log_text_browser, "HCI_Dump_Logs")

        # Start bluetoothd logs
        self.bluez_logger.start_bluetoothd_logs(self.bluetoothd_log_text_browser)
        '''
        #self.bluez_logger.bluetoothd_file_position=0
        #content = self.bluez_logger.bluetoothd_logfile_fd.read(self.bluez_logger.bluetoothd_file_position)
        #self.bluetoothd_log_text_browser.append(content)
        #self.bluez_logger.bluetoothd_file_position = self.bluez_logger.bluetoothd_logfile_fd.tell()
        '''

        # Start pulseaudio logs

        self.bluez_logger.start_pulseaudio_logs(self.pulseaudio_log_text_browser)
        '''
        ##self.bluez_logger.pulseaudio_file_position=0
        ##self.bluez_logger.pulseaudio_logfile_fd.seek(self.bluez_logger.pulseaudio_file_position)
        #content1 = self.bluez_logger.pulseaudio_logfile_fd.read()
        #self.pulseaudio_log_text_browser.append(content1)
        #self.bluez_logger.pulseaudio_file_position = self.bluez_logger.pulseaudio_logfile_fd.tell()
        '''

        # Start HCI dump logs
        self.bluez_logger.start_dump_logs(
            interface=self.interface,
            log_text_browser=self.hci_dump_log_text_browser)

        '''
        #self.bluez_logger.file_position=0
        #self.bluez_logger.logfile_fd.seek(self.bluez_logger.file_position)
        #content2 = self.bluez_logger.logfile_fd.read()
        #self.hci_dump_log_text_browser.append(content2)
        #self.bluez_logger.file_position = self.bluez_logger.logfile_fd.tell()
        '''
        # Set the main layout for the test application window

        back_button = QPushButton("Back")
        back_button.setStyleSheet("font-size: 16px; padding: 6px;")

        back_button.clicked.connect(self.back_callback)
        # Create horizontal layout to hold back button
        back_button_layout = QHBoxLayout()
        back_button_layout.addWidget(back_button)
        back_button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_grid_layout.addLayout(back_button_layout, 11, 0, 1, 1)  # Row 11, column 0

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        main_content_widget = QWidget()
        main_content_widget.setLayout(self.main_grid_layout)
        scroll_area.setWidget(main_content_widget)

        final_layout = QVBoxLayout()
        final_layout.addWidget(scroll_area)
        self.setLayout(final_layout)

    def profile_selected(self):
        """
        Handles profile selection from the list.

        - If GAP is selected, shows GAP controls.
        - If a device under GAP is selected, shows available profiles for that device.
        """

        selected_item = self.profiles_list_widget.currentItem()
        if not selected_item:
            return

        selected_text = selected_item.text()
        bold_font = QFont()
        bold_font.setBold(True)

        # Clear existing methods widget
        if hasattr(self, 'profile_methods_widget'):
            self.profile_methods_widget.deleteLater()

        # Check if device was selected (indented by two spaces)
        if selected_text.startswith("  "):
            device_name = selected_text.strip()

            self.profile_description_text_browser.clear()
            self.profile_description_text_browser.setFont(bold_font)
            self.profile_description_text_browser.append(f"Device Selected: {device_name}")
            self.profile_description_text_browser.append("Available Profiles for this device:")

            # Create list of available profiles for this device (hardcoded here, replace with dynamic query if needed)
            available_profiles = ["A2DP", "OPP", "HFP"]

            profiles_layout = QVBoxLayout()
            for profile in available_profiles:
                profile_button = QPushButton(profile)
                profile_button.setFont(bold_font)
                profile_button.setStyleSheet("color:blue;")
                # Optional: use lambda to pass both device and profile
                profile_button.clicked.connect(lambda _, d=device_name, p=profile: self.load_profile_ui(d, p))
                profiles_layout.addWidget(profile_button)

            profile_widget = QWidget()
            profile_widget.setLayout(profiles_layout)

            self.profile_methods_layout = QHBoxLayout()
            self.profile_methods_layout.addWidget(profile_widget)
            self.profile_methods_widget = QWidget()
            self.profile_methods_widget.setLayout(self.profile_methods_layout)
            self.findChild(QGridLayout).addWidget(self.profile_methods_widget, 2, 2, 3, 1)
            return

        elif selected_text == "GAP":
            self.profile_description_text_browser.clear()
            self.profile_description_text_browser.append("GAP Profile Selected")
            self.profile_description_text_browser.setFont(bold_font)
            self.profile_description_text_browser.append("Use the below methods as required:")

            # Build GAP UI (existing GAP UI code retained here)
            self.gap_methods_layout = QVBoxLayout()
            set_discoverable_label = QLabel("SetDiscoverable:")
            set_discoverable_label.setFont(bold_font)
            set_discoverable_label.setStyleSheet("color:black")
            self.gap_methods_layout.addWidget(set_discoverable_label)

            set_discoverable_timeout_layout = QHBoxLayout()
            set_discoverable_timeout_label = QLabel("SetDiscoverable Timeout:")
            set_discoverable_timeout_label.setFont(bold_font)
            set_discoverable_timeout_label.setStyleSheet("color:blue;")
            set_discoverable_timeout_layout.addWidget(set_discoverable_timeout_label)
            self.discoverable_timeout_input = QLineEdit("0")
            set_discoverable_timeout_layout.addWidget(self.discoverable_timeout_input)
            self.gap_methods_layout.addLayout(set_discoverable_timeout_layout)

            discoverable_buttons_layout = QHBoxLayout()
            self.set_discoverable_on_button = QPushButton("ON")
            self.set_discoverable_on_button.setFont(bold_font)
            self.set_discoverable_on_button.setStyleSheet("color:green;")
            self.set_discoverable_on_button.clicked.connect(self.set_discoverable_on)
            discoverable_buttons_layout.addWidget(self.set_discoverable_on_button)

            self.set_discoverable_off_button = QPushButton("OFF")
            self.set_discoverable_off_button.setFont(bold_font)
            self.set_discoverable_off_button.setStyleSheet("color:red;")
            self.set_discoverable_off_button.clicked.connect(self.set_discoverable_off)
            self.set_discoverable_off_button.setEnabled(False)
            discoverable_buttons_layout.addWidget(self.set_discoverable_off_button)
            self.gap_methods_layout.addLayout(discoverable_buttons_layout)

            refresh_button_layout_discoverable = QVBoxLayout()
            self.refresh_button_discoverable = QPushButton("REFRESH")
            self.refresh_button_discoverable.setEnabled(True)
            self.refresh_button_discoverable.clicked.connect(self.refresh_discoverable)
            self.refresh_button_discoverable.setFont(bold_font)
            self.refresh_button_discoverable.setStyleSheet("color:green;")
            refresh_button_layout_discoverable.addWidget(self.refresh_button_discoverable)
            self.gap_methods_layout.addLayout(refresh_button_layout_discoverable)

            # Inquiry section
            inquiry_label = QLabel("Inquiry:")
            inquiry_label.setFont(bold_font)
            inquiry_label.setStyleSheet("color:black")
            self.gap_methods_layout.addWidget(inquiry_label)

            inquiry_timeout_layout = QHBoxLayout()
            inquiry_timeout_label = QLabel("Inquiry Timeout:")
            inquiry_timeout_label.setFont(bold_font)
            inquiry_timeout_label.setStyleSheet("color:blue;")
            inquiry_timeout_layout.addWidget(inquiry_timeout_label)
            self.inquiry_timeout_input = QLineEdit("0")
            inquiry_timeout_layout.addWidget(self.inquiry_timeout_input)
            self.gap_methods_layout.addLayout(inquiry_timeout_layout)

            discovery_buttons_layout = QHBoxLayout()
            self.set_discovery_on_button = QPushButton("START")
            self.set_discovery_on_button.setFont(bold_font)
            self.set_discovery_on_button.setStyleSheet("color:green;")
            self.set_discovery_on_button.setEnabled(True)
            self.set_discovery_on_button.clicked.connect(self.set_discovery_on)
            discovery_buttons_layout.addWidget(self.set_discovery_on_button)

            self.set_discovery_off_button = QPushButton("STOP")
            self.set_discovery_off_button.setFont(bold_font)
            self.set_discovery_off_button.setStyleSheet("color:red;")
            self.set_discovery_off_button.clicked.connect(self.set_discovery_off)
            self.set_discovery_off_button.setEnabled(False)
            discovery_buttons_layout.addWidget(self.set_discovery_off_button)
            self.gap_methods_layout.addLayout(discovery_buttons_layout)

            refresh_button_layout = QVBoxLayout()
            self.refresh_button = QPushButton("REFRESH")
            self.refresh_button.setEnabled(True)
            self.refresh_button.clicked.connect(self.refresh)
            self.refresh_button.setFont(bold_font)
            self.refresh_button.setStyleSheet("color:green;")
            refresh_button_layout.addWidget(self.refresh_button)
            self.gap_methods_layout.addLayout(refresh_button_layout)

            gap_methods_widget = QWidget()
            gap_methods_widget.setLayout(self.gap_methods_layout)

            self.profile_methods_layout = QHBoxLayout()
            self.profile_methods_layout.addWidget(gap_methods_widget)
            self.profile_methods_widget = QWidget()
            self.profile_methods_widget.setLayout(self.profile_methods_layout)
            self.findChild(QGridLayout).addWidget(self.profile_methods_widget, 2, 2, 3, 1)

    def load_profile_ui(self, device_name, profile):
        """
        Load and display UI for the selected profile of a device.

        Args:
            device_name (str): Selected device
            profile (str): Profile name like 'A2DP', 'OPP', etc.
        """
        print(f"Loading profile '{profile}' for device '{device_name}'")

        self.profile_description_text_browser.clear()
        self.profile_description_text_browser.append(f"{profile} Profile selected for {device_name}")

        # Add your logic to load the A2DP/OPP/HFP interface here
        # For example:
        if profile == "A2DP":
            self.profile_description_text_browser.clear()
            self.profile_description_text_browser.append("A2DP Profile Selected")
            self.profile_description_text_browser.setFont(bold_font)
            self.profile_description_text_browser.append("Choose A2DP Role: Source or Sink")

            # Clear any previous widgets
            if hasattr(self, 'profile_methods_widget'):
                self.profile_methods_widget.setParent(None)

            # Create sub-tabs for A2DP roles
            self.a2dp_tab_widget = QTabWidget()
            bold_font = QFont()
            font.setBold(True)
            # Build Source and Sink tabs
            self.a2dp_tab_widget.setFont(bold_font)
            self.a2dp_tab_widget.addTab(self.build_a2dp_source_tab(device_name), "A2DP Source")
            self.a2dp_tab_widget.addTab(self.build_a2dp_sink_tab(device_name), "A2DP Sink")
            self.a2dp_tab_widget.setStyleSheet("color:black;")

            # Add to the profile methods area
            self.profile_methods_layout = QHBoxLayout()
            self.profile_methods_layout.addWidget(self.a2dp_tab_widget)
            self.profile_methods_widget = QWidget()
            self.profile_methods_widget.setLayout(self.profile_methods_layout)
            self.findChild(QGridLayout).addWidget(self.profile_methods_widget, 2, 2, 3, 1)

        elif profile == "OPP":
            self.profile_description_text_browser.clear()
            self.profile_description_text_browser.append("OPP Profile Selected")
            self.profile_description_text_browser.setFont(bold_font)
            self.profile_description_text_browser.append("Use the below methods as required:")

            self.opp_methods_layout = QVBoxLayout()
            opp_label = QLabel("OPP Functionality:")
            opp_label.setFont(bold_font)
            self.opp_methods_layout.addWidget(opp_label)

            # Device selection layout
            connected_devices = self.bluetooth_device_manager.get_connected_devices()
            device_selection_layout = QHBoxLayout()
            device_label = QLabel("Select Device:")
            device_label.setFont(bold_font)
            device_label.setStyleSheet("color:blue;")
            device_selection_layout.addWidget(device_label)
            self.device_selector = QComboBox()
            for address, name in connected_devices.items():
                self.device_selector.addItem(f"{name} ({address})", address)
            self.device_selector.currentIndexChanged.connect(self.on_device_selected_for_a2dp)
            device_selection_layout.addWidget(self.device_selector)
            self.opp_methods_layout.addLayout(device_selection_layout)

            # OPP select file location
            set_opp_file_location_layout = QHBoxLayout()
            set_opp_file_location_label = QLabel("Select File:")
            set_opp_file_location_label.setFont(bold_font)
            set_opp_file_location_label.setStyleSheet("color:blue;")
            set_opp_file_location_layout.addWidget(set_opp_file_location_label)
            self.opp_location_input = QLineEdit()
            self.opp_location_input.setReadOnly(True)
            set_opp_file_location_layout.addWidget(self.opp_location_input)
            self.browse_opp_button = QPushButton("Browse")
            self.browse_opp_button.clicked.connect(self.browse_opp_file)
            set_opp_file_location_layout.addWidget(self.browse_opp_button)
            self.opp_methods_layout.addLayout(set_opp_file_location_layout)

            # OPP methods such as send file and receive file buttons
            opp_buttons_layout = QHBoxLayout()
            self.send_file_button = QPushButton("Send File")
            self.send_file_button.setFont(bold_font)
            self.send_file_button.setStyleSheet("color:green;")
            self.send_file_button.clicked.connect(self.send_file)
            opp_buttons_layout.addWidget(self.send_file_button)
            self.opp_methods_layout.addLayout(opp_buttons_layout)

            bold_font = QFont()
            bold_font.setBold(True)
            self.receive_file_button = QPushButton("Receive File")
            self.receive_file_button.setFont(bold_font)
            self.receive_file_button.setStyleSheet("color:red;")
            self.receive_file_button.clicked.connect(self.receive_file)
            opp_buttons_layout.addWidget(self.receive_file_button)

            # Creating opp methods widget which will hold opp_methods_layout
            opp_methods_widget = QWidget()
            opp_methods_widget.setLayout(self.opp_methods_layout)

            # Add opp methods widget to Profile Methods or Procedures
            self.profile_methods_layout = QHBoxLayout()
            self.profile_methods_layout.addWidget(opp_methods_widget)
            self.profile_methods_widget = QWidget()
            self.profile_methods_widget.setLayout(self.profile_methods_layout)
            self.findChild(QGridLayout).addWidget(self.profile_methods_widget, 2, 2, 3, 1)

    def add_device(self, device_name):
        """
        Adds a device name below the GAP profile in the list if not already present.
        Args:
            device_name (str): The paired/connected device name
        """
        # Find GAP index
        for i in range(self.profiles_list_widget.count()):
            if self.profiles_list_widget.item(i).text() == "GAP":
                gap_index = i
                break
        else:
            return  # GAP not found

        # Check if device is already added
        for i in range(self.profiles_list_widget.count()):
            if self.profiles_list_widget.item(i).text() == f"  {device_name}":
                return  # Already added

        # Create indented item for device
        device_item = QListWidgetItem(f"  {device_name}")
        device_item.setFont(QFont("Arial", 10))  # Smaller font
        device_item.setForeground(Qt.GlobalColor.black)  # Optional color

        device_item.setData(Qt.ItemDataRole.UserRole, "device")
        device_item.setData(Qt.ItemDataRole.UserRole + 1, device_name.strip())

        # Insert right below GAP
        self.profiles_list_widget.insertItem(gap_index + 1, device_item)



'''
    def profile_selected(self):
        """
         Handles profile selection from the list.

         Depending on the selected Bluetooth profile (e.g., GAP, A2DP, OPP),
         this function dynamically updates the GUI to show relevant methods,
         controls, and input fields for the selected profile.

         args: None
         returns: None
         """

        selected_profile = self.findChild(QListWidget).currentItem().text()
        bold_font = QFont()
        bold_font.setBold(True)
        if hasattr(self, 'profile_methods_widget'):
            self.profile_methods_widget.deleteLater()

        if selected_profile == "GAP":
            self.profile_description_text_browser.clear()
            self.profile_description_text_browser.append("GAP Profile Selected")
            self.profile_description_text_browser.setFont(bold_font)
            self.profile_description_text_browser.append("Use the below methods as required:")

            # Creating discoverable timeout input window along with SetDiscoverable ON/OFF
            self.gap_methods_layout = QVBoxLayout()
            set_discoverable_label = QLabel("SetDiscoverable:")
            set_discoverable_label.setFont(bold_font)
            set_discoverable_label.setStyleSheet("color:black")
            self.gap_methods_layout.addWidget(set_discoverable_label)
            set_discoverable_timeout_layout = QHBoxLayout()
            set_discoverable_timeout_label = QLabel("SetDiscoverable Timeout:")
            set_discoverable_timeout_label.setFont(bold_font)
            set_discoverable_timeout_label.setStyleSheet("color:blue;")
            set_discoverable_timeout_layout.addWidget(set_discoverable_timeout_label)
            self.discoverable_timeout_input = QLineEdit("0")
            set_discoverable_timeout_layout.addWidget(self.discoverable_timeout_input)
            self.gap_methods_layout.addLayout(set_discoverable_timeout_layout)

            discoverable_buttons_layout = QHBoxLayout()
            self.set_discoverable_on_button = QPushButton("ON")
            self.set_discoverable_on_button.setFont(bold_font)
            self.set_discoverable_on_button.setStyleSheet("color:green;")
            self.set_discoverable_on_button.clicked.connect(self.set_discoverable_on)
            discoverable_buttons_layout.addWidget(self.set_discoverable_on_button)
            self.set_discoverable_off_button = QPushButton("OFF")
            self.set_discoverable_off_button.setFont(bold_font)
            self.set_discoverable_off_button.setStyleSheet("color:red;")
            self.set_discoverable_off_button.clicked.connect(self.set_discoverable_off)
            self.set_discoverable_on_button.setEnabled(True)
            self.set_discoverable_off_button.setEnabled(False)
            discoverable_buttons_layout.addWidget(self.set_discoverable_off_button)
            self.gap_methods_layout.addLayout(discoverable_buttons_layout)

            refresh_button_layout_discoverable = QVBoxLayout()
            self.refresh_button_discoverable = QPushButton("REFRESH")
            self.refresh_button_discoverable.setEnabled(True)
            self.refresh_button_discoverable.clicked.connect(self.refresh_discoverable)
            self.refresh_button_discoverable.setFont(bold_font)
            self.refresh_button_discoverable.setStyleSheet("color:green;")
            refresh_button_layout_discoverable.addWidget(self.refresh_button_discoverable)
            self.gap_methods_layout.addLayout(refresh_button_layout_discoverable)

            # Creating GAP Methods Layout with Inquiry timeout along with StartDiscovery and StopDiscovery
            inquiry_label = QLabel("Inquiry:")
            inquiry_label.setFont(bold_font)
            inquiry_label.setStyleSheet("color:black")
            self.gap_methods_layout.addWidget(inquiry_label)
            self.gap_methods_layout.addLayout(set_discoverable_timeout_layout)
            inquiry_timeout_layout = QHBoxLayout()
            inquiry_timeout_label = QLabel("Inquiry Timeout:")
            inquiry_timeout_label.setFont(bold_font)
            inquiry_timeout_label.setStyleSheet("color:blue;")
            inquiry_timeout_layout.addWidget(inquiry_timeout_label)
            self.inquiry_timeout_input = QLineEdit("0")
            inquiry_timeout_layout.addWidget(self.inquiry_timeout_input)
            self.gap_methods_layout.addLayout(inquiry_timeout_layout)

            discovery_buttons_layout = QHBoxLayout()
            self.set_discovery_on_button = QPushButton("START")
            self.set_discovery_on_button.setFont(bold_font)
            self.set_discovery_on_button.setStyleSheet("color:green;")
            self.set_discovery_on_button.setEnabled(True)
            self.set_discovery_on_button.clicked.connect(self.set_discovery_on)
            discovery_buttons_layout.addWidget(self.set_discovery_on_button)
            self.set_discovery_off_button = QPushButton("STOP")
            self.set_discovery_off_button.setFont(bold_font)
            self.set_discovery_off_button.setStyleSheet("color:red;")
            self.set_discovery_off_button.clicked.connect(self.set_discovery_off)
            self.set_discovery_off_button.setEnabled(False)
            discovery_buttons_layout.addWidget(self.set_discovery_off_button)
            self.gap_methods_layout.addLayout(discovery_buttons_layout)

            refresh_button_layout = QVBoxLayout()
            self.refresh_button = QPushButton("REFRESH")
            self.refresh_button.setEnabled(True)
            self.refresh_button.clicked.connect(self.refresh)
            self.refresh_button.setFont(bold_font)
            self.refresh_button.setStyleSheet("color:green;")
            refresh_button_layout.addWidget(self.refresh_button)
            self.gap_methods_layout.addLayout(refresh_button_layout)

            # Creating GAP methods widget which will hold gap_methods_layout
            gap_methods_widget = QWidget()
            gap_methods_widget.setLayout(self.gap_methods_layout)

            # Add Gap methods widget to Profile Methods or Procedures
            self.profile_methods_layout = QHBoxLayout()
            self.profile_methods_layout.addWidget(gap_methods_widget)
            self.profile_methods_widget = QWidget()
            self.profile_methods_widget.setLayout(self.profile_methods_layout)
            self.findChild(QGridLayout).addWidget(self.profile_methods_widget, 2, 2, 3, 1)
'''