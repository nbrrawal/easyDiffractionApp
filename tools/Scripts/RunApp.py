__author__ = "github.com/AndrewSazonov"
__version__ = '0.0.1'

import os, sys
import Functions, Config


CONFIG = Config.Config()

def appExePath():
    d = {
        'macos': os.path.join(CONFIG.installation_dir, CONFIG.app_full_name, 'Contents', 'MacOS', CONFIG.app_name),
        'ubuntu': os.path.join(CONFIG.installation_dir, CONFIG.app_name, CONFIG.app_full_name),
        'windows': os.path.join(CONFIG.installation_dir, CONFIG.app_name, CONFIG.app_full_name)
    }
    return d[CONFIG.os]

def runApp():
    Functions.printNeutralMessage(f'Installed application exe path: {appExePath()}')
    print("ATTEMPT TO RUN {}".format(str({CONFIG.app_name})))
    try:
        message = f'run {CONFIG.app_name}'
        if len(sys.argv) == 1:
            print(">> 1")
            Functions.run(appExePath())
        else:
            print(">> 2")
            #if 'test' in sys.argv[1:]:
            #    Functions.createDir(CONFIG.screenshots_dir)
            print('RUNNING {}'.format(str(appExePath())))
            # Functions.run(appExePath(), *sys.argv[1:])
    except Exception as exception:
        Functions.printFailMessage(message, exception)
        sys.exit()
    else:
        Functions.printSuccessMessage(message)

if __name__ == "__main__":
    runApp()
