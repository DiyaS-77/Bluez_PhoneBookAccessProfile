import dbus
import time


class PhoneBookAccess:
    """
    A client class to interact with the Bluetooth Phone Book Access Profile (PBAP)
    using BlueZ's OBEX and D-Bus interface.
    """

    def __init__(self):
        """
        Initialize the PhoneBookAccess client and prepare the OBEX session.

        :arg-- device_address: Bluetooth MAC address of the PBAP-supported device
        """
        self.bus = dbus.SessionBus()
        self.client = dbus.Interface(self.bus.get_object("org.bluez.obex", "/org/bluez/obex"), "org.bluez.obex.Client1")
        self.session_path = None
        self.phonebook = None

    def create_session(self,device_address):
        """
        Create a PBAP OBEX session with the remote device.
        """
        args = {"Target": dbus.String("PBAP")}
        self.session_path = self.client.CreateSession(device_address, args)
        print(f" Session created at: {self.session_path}")

        time.sleep(1)

        self.phonebook = dbus.Interface(
            self.bus.get_object("org.bluez.obex", self.session_path),
            "org.bluez.obex.PhonebookAccess1")

    def select_phonebook(self, location, folder):
        """
        Select a specific phonebook to interact with.
        args---  
        : location: Phonebook storage location (e.g., "internal", "sim1")
        : folder: Phonebook type (e.g., "pb", "ich", "och", "mch")
        """
        if not self.phonebook:
            print(" Phonebook interface not initialized.")
            return
        self.phonebook.Select(location,folder)
        print(f"Selected {location}/{folder} phonebook.")

    def get_size(self):
        """
        Get the number of entries in the currently selected phonebook.
        """
        if self.phonebook:
            size = self.phonebook.GetSize()
            print(f"Phonebook size: {size}")
        else:
            print(" Phonebook interface not ready.")
    
    def list_filters(self):
        """
        List available vCard filter fields, excluding BIT-based reserved fields.
        """
        fields = self.phonebook.ListFilterFields()
        print("Available Filter Fields:")
        for field in fields:
            if not field.startswith("BIT"):
                print(f" - {field}")

    def list_contacts(self):
        """
        List all contacts (vCard handle and name) from the current phonebook.
        """
        contacts = self.phonebook.List({})
        for vcard, name in contacts:
            print(f"{vcard} - {name}")

    def pull(self, vcard_handle, target_file="/tmp/single.vcf",fields=None):
        """
        Pull a specific vCard file from the phonebook.
        args---
        : vcard_handle: vCard file handle (e.g. "1.vcf")
        : target_file: File path to store the vCard locally
        """
        filters={}
        if fields:
            filters["Fields"]=dbus.Array(fields,signature='s')
            print(f"Applying fields filter: {fields}")
        print(f"Pulling vCard: {vcard_handle} to {target_file}")
        transfer_path, props = self.phonebook.Pull(vcard_handle, target_file,filters)
        print(f" Pulled {vcard_handle} to {target_file}")
    
    def pull_all(self, target_file="/tmp/pb.vcf"):
        """
        Pull the full phonebook and save it to a local file.

        :arg -- target_file: File path to store the full phonebook
        """
        print(" Pulling full phonebook...")
        transfer_obj, transfer_props = self.phonebook.PullAll(target_file, {})
        print(f" PullAll complete. File saved: {target_file}")

    def search_contacts(self, search_field, search_value):
        """
        Search for contacts by a specific field and value.
        args----
        : search_field: The field to search by ("name", "number", or "sound")
        : search_value: The value to search for
        """
        print(f"Searching contacts by {search_field}: {search_value}")
        results = self.phonebook.Search(search_field, search_value, {})
        for vcard, search_field in results:
            print(f"Found: {vcard} - {search_field}")

    def disconnect(self):
        """
        Remove the OBEX session.
        """
        if self.session_path:
            self.client.RemoveSession(self.session_path)
            print("Session removed.")
            self.session_path = None

    def get_property(self, prop_name):
        """
        Retrieve a single property from the phonebook access interface.

        :arg--- prop_name: The name of the property to retrieve
        """
        props_iface = dbus.Interface(
        self.bus.get_object("org.bluez.obex", self.session_path),
        "org.freedesktop.DBus.Properties"
         )
  
        value = props_iface.Get("org.bluez.obex.PhonebookAccess1", prop_name)
        print(f"{prop_name} = {value}")
        

