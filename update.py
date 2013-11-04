# ENCODE Tools functions
from ENCODETools import get_ENCODE
from ENCODETools import patch_ENCODE
from ENCODETools import new_ENCODE
from ENCODETools import GetENCODE
#from ENCODETools import KeyENCODE
from ENCODETools import ReadJSON
#from ENCODETools import WriteJSON
from ENCODETools import ValidJSON
from ENCODETools import CleanJSON
from ENCODETools import FlatJSON
#from ENCODETools import EmbedJSON

from identity import data_file
from identity import keys


if __name__ == "__main__":
    '''
    This script will read in all objects in the objects folder, determine if they are different from the database object, and post or patch them to the database.
    Authentication is determined from the keys.txt file.
    '''
    # FUTURE: Should also be deal with errors that are only dependency based.

    # load objects in object folder.  MODIFY TO HAVE USER VIEW AND SELECT OBJECTS
    #object_filenames = os.listdir('objects/')
    
    # run for each object in objects folder
    #for object_filename in object_filenames:
        #if '.json' in object_filename:

    # load object  SHOULD HANDLE ERRORS GRACEFULLY
    print('Opening ' + data_file)
    json_object = ReadJSON(data_file)
    
    # if the returned json object is not a list, put it in one
    if type(json_object) is dict:
        object_list = []
        object_list.append(json_object)
    elif type(json_object) is list:
        object_list = json_object

    for new_object in object_list:
        
        # define object parameters.  NEEDS TO RUN A CHECK TO CONFIRM THESE EXIST FIRST.
        object_type = str(new_object[u'@type'][0])
        object_id = str(new_object[u'@id'])
        object_uuid = str(new_object[u'uuid'])
        object_name = str(new_object[u'accession'])

        # get relevant schema
        object_schema = GetENCODE(('/profiles/' + object_type + '.json'),keys)

        # clean object of unpatchable or nonexistent properties.  SHOULD INFORM USER OF ANYTHING THAT DOESN"T GET PATCHED.
        new_object = CleanJSON(new_object,object_schema)

        new_object = FlatJSON(new_object,keys)

        # check to see if object already exists  
        # PROBLEM: SHOULD CHECK UUID AND NOT USE ANY SHORTCUT METADATA THAT MIGHT NEED TO CHANGE
        # BUT CAN'T USE UUID IF NEW... HENCE PROBLEM
        old_object = GetENCODE(object_id,keys)

#        # test the validity of new object
#        if not ValidJSON(object_type,object_id,new_object):
#            # get relevant schema
#            object_schema = get_ENCODE(('/profiles/' + object_type + '.json'))
#            
#            # test the new object.  SHOULD HANDLE ERRORS GRACEFULLY        
#            try:
#                jsonschema.validate(new_object,object_schema)
#            # did not validate
#            except Exception as e:
#                print('Validation of ' + object_id + ' failed.')
#                print(e)
#
#            # did validate
#            else:
#                # inform the user of the success
#                print('Validation of ' + object_id + ' succeeded.')
#
#                # post the new object(s).  SHOULD HANDLE ERRORS GRACEFULLY
#                response = new_ENCODE(object_collection,new_object)


        # if object is not found, verify and post it
        if old_object.get(u'title') == u'Not Found':

            # test the new object       
            if ValidJSON(object_type,object_id,new_object,keys):
                # post the new object(s).  SHOULD HANDLE ERRORS GRACEFULLY
                response = new_ENCODE(object_type,new_object,keys)

        # if object is found, check for differences and patch it if needed/valid.
        else:
            # flatten original (to match new)
            old_object = FlatJSON(old_object,keys)
            
            # compare new object to old one, remove identical fields.
            for key in new_object.keys():
                if new_object.get(key) == old_object.get(key):
                    new_object.pop(key)

            # if there are any different fields, patch them.  SHOULD ALLOW FOR USER TO VIEW/APPROVE DIFFERENCES
            if new_object:
                
                # inform user of the updates
                print(object_id + ' has updates.')
                #print(new_object)
                
                # patch each field to object individually
                for key,value in new_object.items():
                    patch_single = {}
                    patch_single[key] = value
                    print(patch_single)
                    response = patch_ENCODE(object_id,patch_single,keys)

            # inform user there are no updates            
            else:
                print(object_id + ' has no updates.')

