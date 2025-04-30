from PhonebookProfileMethods import PhoneBookAccess
from methods_library import BluetoothManager

bt_manager=BluetoothManager()       
pbap = PhoneBookAccess()
 
while True:
      print("\n==== Phonebook Access Menu ====")
      print("1. Start device discovery ")
      print("2. Pair with remote device")
      print("3. Connect to remote device")
      print("4. Select Phonebook")
      print("5. Show Phonebook Size")
      print("6. List Contacts (vCards)")
      print("7. Pull Single vCard")
      print("8. Pull Entire Phonebook")
      print("9. Search Contacts")
      print("10. Get a Phonebook Property")
      print("11. List Available Filter Fields")
      print("12. Disconnect and Exit")
      print("===============================")
      
      choice = input(" Choose an option (1-12): ")
      if choice == "1":
         bt_manager.start_discovery()
             
      elif choice == "2"
         bt_manager.pair_device(input('Enter the device address to pair : '))
       
      if choice == "3":
         device_bdaddr=input('Enter the bd_addr of the device you want to connect:')
         pbap.create_session(device_bdaddr)
             
      if choice == "4":
         user_input=input('Select a repository -- Internal/sim1: ')
         folder=input('Enter which pbap object pb,ich,och,mch,fav,spd:')
         pbap.select_phonebook(user_input,folder)
 
      elif choice == "5":
         pbap.get_size()
             
      elif choice == "6":
         pbap.list_contacts()
             
      elif choice == '7':
         handle = input("Enter vCard handle (e.g., 1.vcf): ").strip()
         fields=input("Enter the fields to include (comma-separated, leave blank for all): ").strip()
         if fields:
            field_list=[f.strip().upper() for f in fields.split(",") if f.strip()]
            pbap.pull(handle,fields=field_list)
         else:
            pbap.pull(handle)
             
      elif choice == '8':
         pbap.pull_all()
             
      elif choice == '9':
         searchfield=input('Enter the field for search operation :')
         searchvalue=input('Enter the value name/number/sound: ')
         pbap.search_contacts(searchfield,searchvalue)
             
      elif choice == '10':
         prop_name=input('Enter the property name :Folder/DatabaseIdentifier/PrimaryCounter/SecondaryCounter/FixedImageSize: ')
         pbap.get_property(prop_name)
             
      elif choice == '11':
         pbap.list_filters()
             
      elif choice == '12':
         pbap.disconnect()
         break


