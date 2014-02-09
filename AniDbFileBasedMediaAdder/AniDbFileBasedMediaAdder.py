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
import xdm
import json
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

    _allowed_extensions = ('.avi', '.mkv', '.iso', '.mp4', '.ogm')
    stateFile = os.path.join(xdm.DATADIR, 'AniDbFileBasedMediaAdder_state.json')
    _aidToUidLookup = 'AUID'
    _filesLookup = 'Files'
    _search_url = "http://groenlid.no-ip.org/api/anime"
    _details_url = "http://groenlid.no-ip.org/api/animedetails"

    def __init__(self, instance='Default'):
        MediaAdder.__init__(self, instance=instance)

    def runShedule(self):
        if not (self.c.path_to_scan) or not (self.c.anidb_username) or not (self.c.anidb_password):
            return []

        state = self._loadState()

        log.info("AniDB file scan called for dir'%s'" % self.c.path_to_scan)
        files = self._getListOfFiles()
        log.info("Adding new files to queue. Current queue size is %s'" % len(state[self._filesLookup]))
        for file in files:
            state[self._filesLookup].setdefault(file, {'File': file})
        log.info("Added new files to queue and about to save. Current queue size is %s'" % len(state[self._filesLookup]))
        self._saveState(state)
        self._hashFilesInState(state)
        self._getAniDBFileInfoInState(state)

        animes = {}
        for episode_path, episode_data in state[self._filesLookup].items():
            if 'aid' in episode_data:
                if episode_data["aid"] not in animes:
                    animes[episode_data["aid"]] = episode_data["english"]
        out = []

        mtm = common.PM.getMediaTypeManager('de.uranime.anime')[0]
        for aid, name in animes.items():
            uid = self._getUranimeId(aid, name, state)
            if uid == None:
                log.info('Aid %s was not found on uranime matches' % aid)
            else:
                log.info('found matching show for aid %s and returning uranime id %s' % (aid, str(uid)))
                media = self.Media('de.uranime.anime',
                    uid,
                    'uranime',
                    'Anime',
                    name
                )
                media.status = common.DOWNLOADED
                out.append(media)
        return out

    def _getUranimeId(self, aid, animeName, state):
        auIDList = state[self._aidToUidLookup]
        if auIDList.has_key(aid):
            return auIDList[aid]

        payload = {}
        payload['title'] = animeName
        r = requests.get(self._search_url, params=payload)
        log('uranime search url ' + r.url)
        searchresult = r.json()
        uid = None
        for item in searchresult:
            showDetails = requests.get("%s/%s" % (self._details_url, item['id']))
            if showDetails != None:
                fullAnimeDetails = showDetails.json()
                if "connections" in fullAnimeDetails:
                    for connection in fullAnimeDetails["connections"]:
                        if connection["site_id"] == 1 and str(connection["source_id"]) == aid:
                            auIDList[aid] = item['id']
                            self._saveState( state)
                            return item['id']
        return None


    def successfulAdd(self, mediaList):
        """media list is a list off all the stuff to remove
        with the same objs that where returned in runShedule() """
        #if self.c.remove_movies and len(mediaList):
        #    return self._removeFromWatchlist(self.c.username, self.c.password, self.c.apikey, mediaList)


        return True

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

        log.info("Found %s files to process" % len(allFiles))
        return allFiles

    def _hashFilesInState(self, state):
        filesToHash=[]
        for k, v in state[self._filesLookup].items():
            if 'ed2k' not in v:
                filesToHash.append(k)
        if len(filesToHash) > 0:
            count = 0
            for file in anidb.hash.hash_files(filesToHash, False, ('ed2k',), 3):
                log.info('{0} ed2k://|file|{1}|{2}|{3}|{4}'.format('Hashed:', file.name, file.size, file.ed2k, ' (cached)' if file.cached else ''))
                fileDetails = state[self._filesLookup][file.name]
                fileDetails['ed2k'] = file.ed2k
                fileDetails['size'] = file.size
                count += 1
                if count > 10:
                    count = 0
                    self._saveState(state)

            self._saveState(state)
        return None

    def _getAniDBFileInfoInState(self, state):
        filesTolookup = []
        for k, v in state[self._filesLookup].items():
            if 'FoundOnAniDB' not in v and 'ed2k' in v:
                filesTolookup.append(v)
        if filesTolookup:
            count = 0

            a = anidb.AniDB(self.c.anidb_username, self.c.anidb_password)
            try:
                    a.auth()
                    log.info('{0} {1}'.format('Logged in as user:', self.c.anidb_username))
            except anidb.AniDBUserError:
                    log.error('Invalid username/password.')
                    return None
            except anidb.AniDBTimeout:
                    log.error('Connection timed out.')
                    return None
            except anidb.AniDBError as e:
                    log.error('{0} {1}'.format('Fatal error:', e))
                    return None

            for fileDetails in filesTolookup:
                fid = (fileDetails['size'], fileDetails['ed2k'])
                try:
                    info = a.get_file(fid, True)
                    if (info['english'] == ""):
                        info['english'] = info['romaji']
                    log.info('{0} [{1}] {2} ({3}) - {4} - {5} ({6}) -- {7}|{8}'.format(
                        'Identified:', info['gtag'], info['romaji'], info['english'],
                        info['epno'], info['epromaji'], info['epname'], info['aid'], info['eid'])
                    )
                    fileDetails.update(info)
                    fileDetails['FoundOnAniDB'] = True
                    count += 1
                    if count > 10:
                        count = 0
                        self._saveState(state)

                except anidb.AniDBUnknownFile:
                    log.info('Unknown file. %s' % file.name)
                    fileDetails['FoundOnAniDB'] = False
            self._saveState(state)
            return None

    def _loadState(self):
        state = {}
        if os.path.isfile(self.stateFile):
            log.debug("Loading AniDBMediaAdder state from %s" % self.stateFile)
            with open(self.stateFile, "r") as stateData:
                state = json.loads(stateData.read())
        state.setdefault(self._aidToUidLookup,{})
        state.setdefault(self._filesLookup,{})
        return state

    def _saveState(self, state):
        log.debug("saving AniDBMediaAdder state to %s" % self.stateFile)
        with open(self.stateFile, "w") as stateData:
            stateData.write(json.dumps(state))

    def _utf8Encoder(self, unicodeCsvData):
        for line in unicodeCsvData:
            yield line.encode('utf-8')
