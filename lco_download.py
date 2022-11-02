#!/usr/bin/env python -B -u

"""
Script to download observations from the LCO archive
Eric Jensen, Oct. 2022  ejensen1@swarthmore.edu 
Copyright Eric Jensen, 2022

Pre-requisite package that is not in the Python standard library:
    requests      # for HTTP requests
    
Optional (but highly recommended) packages for better performance: 
    tqdm          #  for nice progress bars
    aiohttp       #  for multiple file downloads in parallel
    nest_asyncio  #  only needed if running from Spyder IDE

To install packages, use 'pip install [packagename]' or 
    'conda install [packagename]'
    
Older versions of Spyder are known to cause issues.  Update to 
5.3.3 or newer for best results.  If using anaconda, open the 
Anaconda prompt (Windows) or a Terminal window (Mac) and type
  'conda update anaconda'
This should update Spyder and all its dependencies (as well as
other packages you have installed).
    
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program, in the file COPYING.txt.  If not, see
<http://www.gnu.org/licenses/>.

"""

# Put your LCO API access token here.  You can find this by logging 
# into the LCO observing portal at https://observe.lco.global and 
# then clicking in the upper right to access your account profile. 
token = "";

# Set this to False if you prefer to enter parameters for
# each query manually rather than using command-line
# arguments.  If you do that, see the routine
# hardcoded_args just below to enter desired arguments.
# Set this to True to enter search info on the command line. 

use_command_line_args = True

def hardcoded_args():
    '''
    If you prefer to edit the script rather than specifying
    command-line parameters, set your params below, and set
    use_command_line_args = False above.  
    '''
    args = argparse.Namespace()
    # Request ID to download; this is listed in the LCO observing 
    # portal detail page under "Sub-requests", or is the number
    # given in the URL for the detailed observation page. 
    args.requestid = 3001575
    # Directory to save downloads; '.' is the directory from 
    # which the script is being run. 
    args.directory = '.'
    # Frame to start at in sequence:
    args.start = 1
    # Download raw data (rather than reduced):
    args.raw = False
    # Only display count of frames, no download:
    args.count_only = False
    # Number of frames per filter to download; -1 means all frames
    args.numframes = -1
    # Whether to download all in a zipfile (vs. individual files)
    args.zipfile = False
    # Number of simultaneous downloads
    args.streams = 6
    # Filter to download; '' means all available filters. 
    args.filter = ''
    # Enter your token here if you don't have it at the top: 
    args.token = ''
    
    return args


import requests
import argparse
import sys
import os
import re

try:
    import aiohttp
    # To run asynchronous I/O in Spyder we need to activate another 
    # package as well:
    if 'SPYDER_ARGS' in os.environ:
        spyder = True
        try:
            import nest_asyncio
            nest_asyncio.apply()
            run_async = True
        except ImportError:
            print('\nParallel downloads in Spyder require the nest_asyncio package.\n')
            run_async = False
    else:
        # Not running Spyder, async works fine as-is:
        run_async = True
except ImportError:
    print('\nConsider installing aiohttp to allow parallel downloads.')
    run_async = False
    
import asyncio
import time

# Install the tqdm library for nicer progress bars
try:
    import tqdm
    show_progress = True
    if run_async:
        try:
            import tqdm.asyncio
        except ImportError:
            print('\nUpdate to tqdm >= 4.62 to show download progess.')
except ImportError:
    print('\nConsider installing tqdm to show download progess.')
    show_progress = False


def get_args():
    '''Parses and returns arguments passed in'''
    parser = argparse.ArgumentParser(
        description='Script downloads data on LCO')
    parser.add_argument(
        '-r', '--requestid', type=str,
        help='Request ID (e.g. 1234567)',
        default="None", required=True)
    parser.add_argument(
        '-d', '--directory', type=str,
        help='Directory for downloads',
        default=".", required=False)
    parser.add_argument(
        '-f', '--filter', type=str,
        help='Filter to download (default: all)',
        default="", required=False)
    parser.add_argument(
        '-n', '--numframes', type=int,
        help='Maximum number of frames per filter to download (default: all)',
        default=-1, required=False)
    parser.add_argument(
        '-s', '--start', type=int,
        help='First image to download (default: 1)',
        default=1, required=False)
    parser.add_argument(
        '--raw', default=False,
        help='Download raw data (default is reduced data)',
        action='store_true', required=False)
    parser.add_argument(
        '--count_only', default=False,
        help='Only display count of images, no download',
        action='store_true', required=False)
    parser.add_argument(
        '-z', '--zipfile', default=False,
        help='Download each filter\'s files all at once in a zipfile',
        action='store_true', required=False)
    parser.add_argument(
        '--streams', type=int,
        help='Number of simultaneous downloads (default=6)',
        default=6, required=False)
    # Can hard-code token in the lines above, or pass it here on the 
    # comnmand line if you prefer not to have it in the script: 
    parser.add_argument(
        '--token', type=str,
        help='LCO API access token',
        default='', required=False)
    args = parser.parse_args()
    
    # Return the namespace containing all the arguments:
    return args


def download_zip(frames, outfile, progbar=True):
    '''Download the list of frames to a zipfile.'''
    
    # Put the list of frame IDs in a JSON object so we can request
    # a zipped file:
    frame_ids = []
    for f in frames:
        frame_ids.append(f["id"])
        
    url = 'https://archive-api.lco.global/frames/zip/'

    with requests.post(url,
                       headers=headers,
                       json={"frame_ids": frame_ids},
                       stream=True) as r:
       r.raise_for_status()
       # So far we've just grabbed the headers, now get the
       # the file in chunks so we don't exceed memory.
       # Set up a progress bar, doing everything in MB:
       filesize = int(r.headers['Content-Length'])
       chunk = 1024 * 1024
       print(f'Downloading {filesize/1024/1024:0.1f} MB file:',
             f'{os.path.basename(outfile)}.')
       # Assign our content iterator flexibly here to work whether
       # or not tqdm is installed:
       if progbar:
          file_iterator = tqdm.tqdm(r.iter_content(chunk_size=chunk),  
                                    total=int(filesize/chunk), unit="MB", 
                                    dynamic_ncols=True)
       else:
          file_iterator = r.iter_content(chunk_size=chunk)
          # Basic counter for progress updates without tqdm:
          last_shown = -1
       downloaded = 0
       with open(outfile, 'wb') as f:
          for chunk in file_iterator:
             f.write(chunk)
             downloaded += len(chunk)
             if not progbar:
                percent = int(100*(downloaded/filesize))
                if (percent % 10 == 0) and (percent > last_shown):
                    print(f'{percent}%...', end='')
                    last_shown = percent
    

def download_individual(frames, output_dir, progbar=True):
    ''' Download frames one at a time. '''
    i = 0
    if progbar:
        frame_iterator = tqdm.tqdm(frames)
    else:
        frame_iterator = frames
    for frame in frame_iterator:
        i += 1
        frame_file = frame['filename']
        output_file = os.path.join(output_dir, frame_file)
        with open(output_file, 'wb') as f:
            f.write(requests.get(frame['url']).content)
        if not progbar:
            print(f'{i} of {n_download}: Frame {frame_file} done.')

async def download_one_image(frame, output_dir, session):
    ''' Asynchronous routine to download a single image. Called
        repeatedly by download_frames_async.
    '''
    
    output_file = os.path.join(output_dir, frame['filename'])
    chunk_size = 1024*10
    try:
        # Set a long timeout, cumulative for the whole download
        async with session.get(url=frame['url'],
            timeout=aiohttp.ClientTimeout(total=7200)) as response:
            status = response.status
            if (status != 200):
                print(f'Request has status {response.status}.')
                response.raise_for_status()
            with open(output_file, 'wb') as f:
                async for chunk in response.content.iter_chunked(chunk_size):
                    f.write(chunk)
            # If we were successful, return None - no need to retry.
            return None
    except Exception as e:
        print(f"{frame['filename']} failed: {repr(e)}. Will retry.")
        # We return the frame so that we can try to fetch it again:
        return frame

async def download_images_async(frames, output_dir,
                                n_streams=6, progbar=True):
    ''' Download images asynchronously in multiple streams. '''
    connector = aiohttp.TCPConnector(limit_per_host=n_streams)
    if progbar:
        gather_func = tqdm.asyncio.tqdm.gather
    else:
        gather_func = asyncio.gather
    async with aiohttp.ClientSession(connector=connector) as session:
        failed_list = await gather_func(*[download_one_image(frame, 
                                                             output_dir, 
                                                             session) \
                                          for frame in frames])
        # Return the output of the gather call, which may contain one
        # or more frames that weren't successfully downloaded.
        return failed_list

def get_obs_info(request_id, headers):
    '''
    Given a request ID, fetch the information from the LCO
    observation portal API about that observation, specifically
    the filters used, and the defocus setting.
    Input: request_id
    Returns:
        success: True if successfully fetched info, False if not
        defocus: defocus setting
        filters: List of filters used. Even if only one filter, this is still
            in list format, i.e. a one-element list.
        exposure_times: list of exposure times, same order as filter list.
    '''
    # Fetch the observation description from
    # the observation portal.
    try:
        response = requests.get(f'https://observe.lco.global/api/requests/{request_id}/', 
                                headers=headers)
        r = response.json()
        # Get the start window; we only want the date, so strip the rest.
        # The field is formatted like this: "2022-09-19T06:36:00Z"
        date_string = re.sub('T.*', '', r['windows'][0]['start'])

        config = r['configurations'][0]
        # Older observations don't have the 'defocus' field in the 
        # config info, so check first before accessing: 
        if 'defocus' in config['instrument_configs'][0]['extra_params']:
            defocus = config['instrument_configs'][0]['extra_params']['defocus']
        else:
            defocus = None
        if (config['instrument_type'] == '2M0-SCICAM-MUSCAT'):
            filter_list = ['gp', 'rp', 'ip', 'zs']
            # Put them in the same order as filters above:
            par = config['instrument_configs'][0]['extra_params']
            exposure_times = [par['exposure_time_g'],
                              par['exposure_time_r'],
                              par['exposure_time_i'],
                              par['exposure_time_z']]
        else:
            filter_list = [c['optical_elements']['filter'] \
                           for c in config['instrument_configs']]
            exposure_times = [c['exposure_time'] \
                              for c in config['instrument_configs']]
    except Exception as e:
        print(f'*** Could not get info for request ID {reqid}: {e}.')
        return False, None, None, None, None
        
    return True, defocus, date_string, filter_list, exposure_times
        

def create_pathname(frame, filters, date_string,
                    defocus=None, exp_time=None):
    '''
    Given an input frame, use the info to create a filename or
    directory string that encodes information about the
    observation, including target, telescope, filter, date, and
    defocus.  Since we had to make a separate HTTP request to
    get the defocus position, this is passed in separately,
    along with the desired filter name and exposure time.
    Defocus and exposure time are optional, and filters may be
    a list or a scalar.
    '''
    
    target = frame['target_name']
    # Target name looks like "TIC 359388309.01 (TOI 4172.01)"
    # Drop spaces:
    target = re.sub(' ', '', target)
    # Drop part in parentheses
    target = re.sub('\(.*\)', '', target)
    # Replace . with -
    target = re.sub('\.', '-', target)
    
    # Map the site name shorthand strings to more informative names:
    obs_names = {'coj': 'SSO', 'cpt': 'SAAO', 'tfn': 'Teid',
                'lsc': 'CTIO', 'elp': 'McD', 'ogg': 'Hal'}
    obs = obs_names[frame['site_id']]
    
    if re.match('ep', frame['instrument_id']):
        telescope = 'M3'
    else:
        # Drop trailing letter from telescope, e.g. '2m0a'
        telescope = re.sub('[a-z]$', '', frame['telescope_id'])
    
    if isinstance(filters, list):
        filterstring = '_'.join(filters)
    else:
        filterstring = filters
        
    path_string = f'{target}_{date_string}_LCO-{obs}-' + \
        f'{telescope}_{filterstring}'
  
    # Optionally append exposure time and defocus if making names
    # for per-filter subdirectories: 
    if exp_time is not None:
        path_string += f'_{int(exp_time)}s'
    if defocus is not None:
        focus_string = re.sub('\.', 'f', f'{defocus:0.1f}')
        path_string += f'_{focus_string}'
        
    return path_string
    
#####################################################
#  Start of the main program
#####################################################


start_time = time.time()

# a is the namespace containing all the arg variables
if use_command_line_args:
    a = get_args()
else:
    a = hardcoded_args()

reqid = a.requestid
start = a.start
raw = a.raw
count_only = a.count_only
output_dir = os.path.expanduser(a.directory)
zipfile = a.zipfile
n_streams = a.streams
filterband = a.filter

# If the token wasn't hard-coded at the top of the script, 
# see if we can get it from arguments: 
if token=='' and 'token' in a:
    if a.token=='':
        print('\n*** Must supply API token for LCO. Either edit script',
              'or pass via --token argument.\n')
        sys.exit(0)
    else:
        token = a.token

# Set numbers for how many frame IDs we request at
# once, based on number the user requests, *and*
# on the API limit of 1000 per query.

# 'numframes' is the number we actually want, and
# 'limit' is how many we ask for per query.

# If 'numframes' is set to -1, the user didn't specify
# and we fetch all frames.
if (a.numframes == -1):
    # Set numframes to a high number so it won't limit us:
    numframes = 1e5
    # This is max we can fetch at one time with API:
    limit = 1000
else:
    numframes = a.numframes
    # Can't get more than 1000 at a time:
    limit = min(1000, numframes)
    
headers = {'Authorization': f'Token {token}'}
frames_url = 'https://archive-api.lco.global/frames/'

success, defocus, date_string, filters, \
    exposure_times = get_obs_info(reqid, headers)
    
if success:
    print(f'Observations starting {date_string}:')
    for f, exp in zip(filters, exposure_times):
        print(f'\tFilter {f}, {exp:0.0f}-second exposures.')
    # Now that we've printed, drop the dashes from the date:
    date_string = re.sub('-', '', date_string)
else:
    print(f'*** Could not fetch information for request ID {reqid}.')
    
print()
if (raw):
    reduction_level = 0
else:
    reduction_level = 91

if (filterband == ''):
    filter_list = filters
    exposure_list = exposure_times
else:
    filter_list = [filterband]
    # Get the right exposure time for that filter:
    try:
        i = filters.index(filterband)
        exposure_list = [exposure_times[i]]
    except ValueError:
        print(f'*** Filter {filterband} is not present in request {reqid}.')
        sys.exit(0)
    
# First download all of the frame information so we know how 
# many images we're dealing with, and can make a container directory. 

# Array of arrays: each entry is an array of the frame info for one filter:
frame_master_list = []
total_frames = 0
for filt in filter_list:
    # Note that the offset is one less than the desired start image number:
    url = f'{frames_url}?request_id={reqid}&' + \
        f'reduction_level={reduction_level}&' + \
        f'primary_optical_element={filt}&' + \
        f'limit={limit}&offset={start - 1}'
        
    # Fetch the frame information:
    print(f'Getting frame information for filter {filt}...')
    response = requests.get(url, headers=headers).json()
    # Make a list of frame information:
    frames = response['results']
    # If there are more than 1000 entries, we don't get them
    # all at once; fetch the rest if needed:
    while (response['next']) and len(frames) < numframes:
        url = response['next']
        remaining = numframes - len(frames)
        if remaining < limit:
            url = re.sub('limit=\d+&', f'limit={remaining}&', url)
        response = requests.get(url, headers=headers).json()
        frames += response['results']

    print(f'Got {len(frames)} total for filter {filt}.\n')

    if len(frames) == 0:
        print('No frames match the query; check parameters and try again.\n')
        sys.exit(0)
    else:
        frame_master_list.append(frames)
        total_frames += len(frames)

# Now create the master directory to hold the downloads: 
if (output_dir == '.'):
    print('Images will be written to the current directory.\n')
else:
    print('Output files will be written to directory',
          f'{output_dir}.\n')

if not count_only and not os.path.exists(output_dir):
    print('Master output directory does not exist, creating it.\n')
    try:
        os.makedirs(output_dir)
    except Exception as e:
        print(f'Could not create output directory {output_dir}.\n')
        print(e)
        sys.exit(0)

# Now the observation-specific directory name: 
pathname_string = create_pathname(frame_master_list[0][0], filter_list,
                                  date_string)
# This will be our actual output directory, so reassign the variable:
output_dir = os.path.join(output_dir, f'{pathname_string}_{total_frames}')

if not count_only and not os.path.exists(output_dir):
    print(f'Creating directory {output_dir}.\n')
    try:
        os.makedirs(output_dir)
    except Exception as e:
        print(f'Could not create output directory {output_dir}.\n')
        print(e)
        sys.exit(0)


# Loop over the filters, and download each one separately:
for filt, expose, frames in zip(filter_list, exposure_list, frame_master_list):

    # Sort by image name so they are in date order; list is
    # usually (always?) in reverse order, so reverse first
    # to speed up sort: 
    frames.reverse()
    frames.sort(key=lambda item: item.get('basename'))

    count = len(frames)
    n_download = min(numframes, count)
   
    print(f'Request ID {reqid} has {count} frames in filter {filt}.')
    
    if (count == 0) or count_only:
        continue
    else:
        print(f'Downloading {n_download} frames starting at',
              f'frame {start}...\n')

            
    pathname_string = create_pathname(frames[0], filt, date_string, 
                                      defocus, expose) + f'_{count}'

    if zipfile:
        output_path = os.path.join(output_dir, f'{pathname_string}.zip')
        download_zip(frames, output_path, show_progress)
    else:
        output_subdir = os.path.join(output_dir, pathname_string)

        if not os.path.exists(output_subdir):
            print(f'Creating subdirectory {pathname_string}.\n')
            try:
                os.makedirs(output_subdir)
            except Exception as e:
                print(f'Could not create output directory {output_subdir}.\n')
                print(e)
                sys.exit(0)

        if run_async:
            retry_count = 0
            max_retries = 5
            download_status = asyncio.run(download_images_async(frames, 
                                                                output_subdir, 
                                                                n_streams,
                                                                show_progress))
            # Get only values that are not None, i.e. the failed frames:
            failed_list = list(filter(None, download_status))
            while (failed_list) and (retry_count < max_retries):
                retry_count += 1
                print(f'Failed to download {len(failed_list)} frames on',
                      f'pass {retry_count}, trying again.\n')
                download_status = asyncio.run(download_images_async(failed_list, 
                                                                    output_subdir, 
                                                                    n_streams))
                failed_list = list(filter(None, download_status))
            if (retry_count == max_retries):
                print('\n*** Failed to download some files: ', failed_list)
            else:
                print('\nAll files downloaded.\n')
        else:
            download_individual(frames, output_subdir, show_progress)

# Comment out if you don't want the beep: 
print('\a\a');
print(f'\nDownload took {(time.time()-start_time)/60:0.1f} minutes.\n')
