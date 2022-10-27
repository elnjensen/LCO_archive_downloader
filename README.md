# Download LCO data easily

This is a Python script to download observations from the [Las Cumbres Observatory (LCO)](https://lco.global/) data archive. 

### Installation

Just save a copy of the script `lco_download.py` to your directory of choice and make it executable, e.g. `chmod +x lco_download.py` in Linux or Mac (from Terminal app). 

### Setup

You'll need your API key from your LCO account.  Log in to the [LCO observation portal](https://observe.lco.global/), and then click on the icon of a person in the upper right and select "Profile".  Your API key will be listed in the upper right of your settings page.  Copy it and paste it into the script for the value of the `token` variable, or if you prefer not to hard-code it, just pass it on the command line with the `--token` switch each time you run the code. 

### Python prerequisites

Pre-requisite package that is not in the Python standard library:
*    [`requests`](https://requests.readthedocs.io/en/latest/)       *(for HTTP requests)*
    
Optional (but highly recommended) packages for better performance: 
*    [`tqdm`](https://tqdm.github.io/)       *(for nice progress bars)*
*    [`aiohttp`](https://docs.aiohttp.org/en/stable/)       *(for multiple file downloads in parallel)*
*    [`nest_asyncio`](https://github.com/erdewit/nest_asyncio)   *(only needed if running from Spyder IDE)*

To install packages, use `pip install [packagename]` or 
    `conda install [packagename]`
    
    
### To run 

You can run the script from the command line.  The RequestID of the observations you want to download is the only required parameter (if you have your API key added to the script).   Type 

`./lco_download.py --help`

to see the command-line options. 

If you prefer, you can edit the script to hard-code any arguments you want to pass, and then run it from within an IDE like [Spyder](https://www.spyder-ide.org/).  To do this, edit the script to change `use_command_line_args` to `False`, and then edit the `hardcoded_args` subroutine to specify your desired arguments. 

Note that older versions of Spyder are known to cause issues.  Update to 
5.3.3 or newer for best results.  If using anaconda, open the 
Anaconda prompt (Windows) or a Terminal window (Mac) and type
  `conda update anaconda`
This should update Spyder and all its dependencies (as well as
other packages you have installed).
    
