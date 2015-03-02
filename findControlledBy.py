import requests
import json
import argparse
import os.path

HEADERS = {'content-type': 'application/json'}
DEBUG_ON = False
SERVER = 'http://www.encodeproject.org'
AUTHID = 'default provided by keypairs.json'
AUTHPW = 'default provided by keypairs.json'
EPILOG = ''' Provide a list of experiments that need a
controlled_by for thier fastqs.  Assumptions are:
If the file has a value in controlled_by then leave it alone.

To use a different key from the default keypair file:

        %(prog)s --key submit
'''


def set_ENCODE_keys(keyfile, key):
        '''
          Set the global authentication keyds
        '''

        keysf = open(keyfile, 'r')
        keys_json_string = keysf.read()
        keysf.close()

        keys = json.loads(keys_json_string)
        key_dict = keys[key]

        global AUTHID
        global AUTHPW
        global SERVER

        AUTHID = key_dict['key']
        AUTHPW = key_dict['secret']
        SERVER = key_dict['server']
        if not SERVER.endswith("/"):
                SERVER += "/"
        return


def get_ENCODE(obj_id):
        '''GET an ENCODE object as JSON and return as dict
        '''
        # url = SERVER+obj_id+'?limit=all&datastore=database'
        url = SERVER+obj_id+'?frame=embedded'
        if DEBUG_ON:
                print "DEBUG: GET %s" % (url)
        response = requests.get(url, auth=(AUTHID, AUTHPW), headers=HEADERS)
        if DEBUG_ON:
                print "DEBUG: GET RESPONSE code %s" % (response.status_code)
                try:
                        if response.json():
                                print "DEBUG: GET RESPONSE JSON"
                                print json.dumps(
                                    response.json(),
                                    indent=4,
                                    separators=(',', ': ')
                                    )
                except:
                        print "DEBUG: GET RESPONSE text %s" % (response.text)
        if not response.status_code == requests.codes.ok:
                return ''
                response.raise_for_status()
        return response.json()


def get_experiment_list(file, search):

        objList = []
        if search == "NULL":
            f = open(file)
            objList = f.readlines()
            for i in range(0, len(objList)):
                objList[i] = objList[i].strip()
        else:
            set = get_ENCODE(search+'&limit=all&frame=embedded')
            for i in range(0, len(set['@graph'])):
                objList.append(set['@graph'][i]['accession'])
                # objList.append(set['@graph'][i]['uuid'])

        return objList


def get_fastq_dictionary(exp):

    controlfiles = {}
    control = get_ENCODE(exp)
    for ff in control['files']:
        if ff.get('file_format') != 'fastq':
            continue
        if 'replicate' not in ff:
            print "Missing replicate error"
            continue
        biorep = str(ff['replicate']['biological_replicate_number'])
        techrep = str(ff['replicate']['technical_replicate_number'])
        pair = str(ff.get('paired_end'))
        rep = biorep + '-' + techrep
        key = rep + '-' + pair
        biokey = biorep + '-' + pair

        if key not in controlfiles:
            controlfiles[key] = [ff['accession']]
        else:
            print "error: replicate-pair has multiple files"
            controlfiles[key].append(ff['accession'])
            controlfiles[key].append('multiple-files-error')

        if biokey not in controlfiles:
            controlfiles[biokey] = [ff['accession']]
        else:
            if ff['accession'] not in controlfiles[biokey]:
                print 'error: control has technical reps'
                controlfiles[biokey].append(ff['accession'])
                controlfiles[biokey].append('tech-reps')
    return controlfiles


def get_HAIB_fastq_dictionary(controls):

    controlfiles = {}
    for i in controls:
        control = get_ENCODE(i)
        for ff in control['files']:
            if ff.get('file_format') != 'fastq':
                continue
            if 'replicate' not in ff:
                print "Missing replicate error"
                continue
            try:
                lib = get_ENCODE(ff['replicate']['library'])
                biosample = lib['biosample']['accession']
            except:
                print 'Cannot find biosample'
                biosample = ''
            pair = str(ff.get('paired_end'))
            key = biosample + '-' + pair

            if key not in controlfiles:
                controlfiles[key] = [ff['accession']]
            else:
                print "error: biosample has multiple files"
                controlfiles[key].append(ff['accession'])
                controlfiles[key].append('same-biosample-error')

    return controlfiles


def main():

    parser = argparse.ArgumentParser(
        description=__doc__, epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )

    parser.add_argument(
        '--infile', '-i',
        default='infile',
        help="File containing a list of ENCSRs.")
    parser.add_argument(
        '--search',
        default='NULL',
        help="The search parameters.")
    parser.add_argument(
        '--key',
        default='default',
        help="The keypair identifier from the keyfile.")
    parser.add_argument(
        '--keyfile',
        default=os.path.expanduser("~/keypairs.json"),
        help="The keypair file.  Default is --keyfile=%s" % (os.path.expanduser("~/keypairs.json")))
    parser.add_argument(
        '--debug',
        default=False,
        action='store_true',
        help="Print debug messages.  Default is False.")
    parser.add_argument(
        '--existing',
        default=False,
        action='store_true',
        help="Print debug messages.  Default is False.")
    args = parser.parse_args()

    DEBUG_ON = args.debug

    set_ENCODE_keys(args.keyfile, args.key)


    objList = get_experiment_list(args.infile, args.search)

    for item in objList:
        print "Experiment:" + item
        obj = get_ENCODE(item)
        controlfiles = {}
        controlIds = []
        for i in obj['possible_controls']:
            controlIds.append(i['accession'])

        # Missing possible controls, bail out
        if 'possible_controls' not in obj or len(obj['possible_controls']) == 0:
            print 'error: {} has no possible_controls'.format(obj['accession'])
            continue

        # If it is HAIB
        elif obj['lab']['name'] == 'richard-myers':
            controlfiles = get_HAIB_fastq_dictionary(controlIds)

        # Single possible control
        elif len(obj['possible_controls']) == 1:
            controlId = obj['possible_controls'][0]['accession']
            controlfiles = get_fastq_dictionary(controlId)

        # Double possible controls
        elif len(obj['possible_controls']) == 2:
            controlId1 = obj['possible_controls'][0]['accession']
            controlfiles1 = get_fastq_dictionary(controlId1)
            controlId2 = obj['possible_controls'][1]['accession']
            controlfiles2 = get_fastq_dictionary(controlId2)
            for x in controlfiles1:
                if x in controlfiles2:
                    controlfiles[x] = controlfiles1[x] + controlfiles2[x]
                else:
                    controlfiles[x] = controlfiles1[x]

        # More than 2 possible controls
        else:
            print 'error: {} has more than 2 possible_controls'.format(obj['accession'])
            continue

        if DEBUG_ON:
            print controlfiles

        # Now find the experiment fastqs
        for ff in obj['files']:
            findold = args.existing or (ff.get('controlled_by') == [] or ff.get('controlled_by') is None)
            if ff.get('file_format') == 'fastq' and findold:
                biorep = str(ff['replicate']['biological_replicate_number'])
                techrep = str(ff['replicate']['technical_replicate_number'])
                pair = str(ff.get('paired_end'))
                rep = biorep + '-' + techrep + '-' + pair
                biokey = biorep + '-' + pair
                print ff['lab']
                if ff['lab'] == '/lab/richard-myers/':
                    print ff['replicate']['library']
                    lib = get_ENCODE(ff['replicate']['library'])

                if rep in controlfiles:
                    answer = controlfiles[rep]
                elif biokey in controlfiles:
                    answer = controlfiles[biokey]
                else:
                    answer = 'error: control had no corresponding replicate'

                print item, controlIds, rep, ff['accession'], answer
        print ''


if __name__ == '__main__':
    main()
