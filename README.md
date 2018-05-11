# PET4L
PET4L [PIVX Emergency Tool For Ledger] is a tool to spend PIVs trapped inside the Ledger Nano S when the Ledger Wallet Chrome App acts crazy.

## Installation
This application does not require installation.<br>
If you are using a binary version, just unzip the folder anywhere you like and use the executable to start the application:
- *Linux*: double-click `pet4l` file inside the `app` directory
- *Windows*: double-click `pet4l.exe` file inside the `app` directory
- *Mac OsX*: double-click `pet4l.app` application folder

If you are running PET4L from the source-code instead, you will need Python3 and several libraries installed.<br>
Needed libraries are listed in `requirements.txt`.<br>
From the `SPMT` directory, launch the tool with:
```bash
python3 pet4l.py
```
To make binary versions from source, [PyInstaller](http://www.pyinstaller.org/) can be used with the `specPet4l.spec` file provided.


## Setup
#### Setting up the RPC server
In order to interact with the PIVX blockchain, PET4L needs a local PIVX wallet running alongside (any empty pivx-cli wallet will do).
Edit your local `pivx.conf` inserting rpcuser, rpcpassword, rpcport and rpcallowip.
Example:
```bash
server=1
rpcuser=myUsername
rpcpassword=myPassword
rpcport=45458
rpcallowip=127.0.0.1
```

Configure the RPC server by clicking on the menu


and inserting the same data
