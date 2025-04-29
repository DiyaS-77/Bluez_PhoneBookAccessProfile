from PhonebookProfileMethods import PhoneBookAccess
from methods_library import BluetoothManager

bt_manager=BluetoothManager()
bt_manager.start_discovery()
bt_manager.Pair(input('Enter the device address to pair : '))
       
pbap = PhoneBookAccess()
 
while True:
      print("\n==== Phonebook Access Menu ====")
      print("1. Connect to remote device")
      print("2. Select Phonebook")
      print("3. Show Phonebook Size")
      print("4. List Contacts (vCards)")
      print("5. Pull Single vCard")
      print("6. Pull Entire Phonebook")
      print("7. Search Contacts")
      print("8. Get a Phonebook Property")
      print("9. List Available Filter Fields")
      print("10. Disconnect and Exit")
      print("===============================")
      
      choice = input(" Choose an option (1-9): ")

      if choice == "1":
         device_bdaddr=input('Enter the bd_addr of the device you want to connect:')
         pbap.create_session(device_bdaddr)
             
      if choice == "1":
         user_input=input('Select a repository -- Internal/sim1: ')
         folder=input('Enter which pbap object pb,ich,och,mch,fav,spd:')
         pbap.select_phonebook(user_input,folder)
 
      elif choice == "2":
         pbap.get_size()
             
      elif choice == "3":
         pbap.list_contacts()
             
      elif choice == '4':
         handle = input("Enter vCard handle (e.g., 1.vcf): ")
         pbap.pull(handle)
             
      elif choice == '5':
         pbap.pull_all()
             
      elif choice == '6':
         searchfield=input('Enter the field for search operation :')
         searchvalue=input('Enter the value name/number/sound: ')
         pbap.search_contacts(searchfield,searchvalue)
             
      elif choice == '7':
         prop_name=input('Enter the property name :Folder/DatabaseIdentifier/PrimaryCounter/SecondaryCounter/FixedImageSize: ')
         pbap.get_property(prop_name)
             
      elif choice == '8':
         pbap.list_filters()
             
      elif choice == '9':
         pbap.disconnect()
         break


