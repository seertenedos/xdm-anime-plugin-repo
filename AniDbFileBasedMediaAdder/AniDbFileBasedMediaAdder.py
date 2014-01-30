# Author: Chris Gilligan
# URL: https://github.com/seertenedos/XDM-main-plugin-repo/
#
# This file is part of a XDM plugin.
#
# XDM plugin.
# Copyright (C) 2013  Dennis Lutter
#
# This plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This plugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/.

from xdm.plugins import *
import anidb, anidb.hash
import fnmatch
import os


import requests
import csv

class AniDbFileBasedMediaAdder(MediaAdder):
    version = "0.1"
    identifier = "seer.AniDbFileBasedMediaAdder"
    addMediaTypeOptions = False
    types = ["de.uranime.anime"]
    screenName = 'AniDB File Processing'
    
    _config = {'path_to_scan': '',
               'anidb_username':'',
               'anidb_password':''}
    config_meta = {'plugin_desc': 'Scans for files to look up on AniDB and to import.',
                   'path_to_scan': {'human': 'Directory to scan'},
                   'anidb_username': {'human': 'AniDB Username'},
                   'anidb_password': {'human': 'AniDB Password'}}

    _allowed_extensions = ('.avi', '.mkv', '.iso', '.mp4')

    def __init__(self, instance='Default'):
        MediaAdder.__init__(self, instance=instance)

    def runShedule(self):
        if not (self.c.path_to_scan) or not (self.c.anidb_username) or not (self.c.anidb_password):
            return []

        log.info("AniDB file scan called for dir'%s'" % self.c.path_to_scan)
        files = self._getListOfFiles()
        hashes = self._hashFiles(files)
        aniDbFileResults = self._getAniDBFileInfo(hashes)
        out = []
        #for movie in movies:
        #    additionalData = {}
        #    additionalData['imdb_id'] = movie['imdb_id']
        #    out.append(self.Media('de.lad1337.movies',
        #                          movie['imdb_id'],
        #                          'tmdb',
        #                          'Movie',
        #                          unicode(movie['title'], 'utf-8'),
        #                          additionalData=additionalData))
        return out

    # get the list of files
    def _getListOfFiles(self):
        allFiles = []
        folderPath = self.c.path_to_scan
        if os.path.isdir(folderPath):
            log.info("Starting file scan on %s" % folderPath)
            for root, dirnames, filenames in os.walk(folderPath):
                log.info("I can see the files %s" % filenames)
                for filename in filenames:
                    if filename.endswith(self._allowed_extensions):
                        if 'sample' in filename.lower():
                            continue
                        curImage = os.path.join(root, filename)
                        allFiles.append(curImage)
                        log.info("Found file: %s" % curImage)
            if not allFiles:
                log.info("No files found!")
                return (False, processLog[0])
        else:
            allFiles = [filePath]

        log.info("Found %s files to process" % len(allFiles))
        return allFiles

    def _hashFiles(self, files):
        cacheHash = True
        hashedFiles = []
        for file in anidb.hash.hash_files(files, cacheHash, ('ed2k',)):
            log.info('{0} ed2k://|file|{1}|{2}|{3}|{4}'.format('Hashed:', file.name, file.size, file.ed2k, ' (cached)' if file.cached else ''))
            hashedFiles.append(file)
        return hashedFiles

    def _getAniDBFileInfo(self, hashedFiles):
        aniDbFileResults = []
        a = anidb.AniDB(self.c.anidb_username, self.c.anidb_password)
        try:
		a.auth()
		log.info('{0} {1}'.format('Logged in as user:', self.c.anidb_username))
	except anidb.AniDBUserError:
		log.error('Invalid username/password.')
		return aniDbFileResults
	except anidb.AniDBTimeout:
		log.error('Connection timed out.')
		return aniDbFileResults
	except anidb.AniDBError as e:
		log.error('{0} {1}'.format('Fatal error:', e))
		return aniDbFileResults

        for file in hashedFiles:
            fid = (file.size, file.ed2k)
            try:
                info = a.get_file(fid, True)
		fid = int(info['fid'])
			
		if (info['english'] == ""): info['english'] = info['romaji']	
		log.info('{0} [{1}] {2} ({3}) - {4} - {5} ({6}) -- {7}|{8}'.format('Identified:', info['gtag'], info['romaji'], info['english'], info['epno'], info['epromaji'], info['epname'], info['aid'], info['eid']))
		aniDbFileResults.append({'HashedFile':file,'AniDBResult':info})
		
	    except anidb.AniDBUnknownFile:
		log.warn('Unknown file. %s' % file.name)
		aniDbFileResults.append({'HashedFile':file})
	return aniDbFileResults;		



		

    def _utf8Encoder(self, unicodeCsvData):
        for line in unicodeCsvData:
            yield line.encode('utf-8')

    # get movie watchlist
    def _getImdbWatchlist(self):
        try:
            r = requests.get(self.c.watchlist_url)
            r.encoding = 'utf-8'
            csvReader = csv.reader(self._utf8Encoder(r.text.splitlines()), dialect=csv.excel)
            header = csvReader.next()
            colId = header.index('const')
            colTitle = header.index('Title')
            movies = []
            for row in csvReader:
                movies.append({'imdb_id':row[colId], 'title':row[colTitle]})
            return movies
        except Exception:
            return []
