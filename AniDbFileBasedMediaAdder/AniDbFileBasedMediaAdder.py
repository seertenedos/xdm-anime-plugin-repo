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

import requests
import csv

class AniDbFileBasedMediaAdder(MediaAdder):
    version = "0.1"
    identifier = "seer.AniDbFileBasedMediaAdder"
    addMediaTypeOptions = False
    types = ["de.uranime.anime"]
    screenName = 'AniDB File Processing'
    
    _config = {'directory_to_scan': ''}
    config_meta = {'plugin_desc': 'Add movies from your http://www.imdb.com watchlist.',
                   'directory_to_scan': {'human': 'Directory to scan for files to look up on AniDB and to import'}}


    def __init__(self, instance='Default'):
        MediaAdder.__init__(self, instance=instance)

    def runShedule(self):
        if not (self.c.directory_to_scan):
            return []
        #movies = self._getImdbWatchlist()
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
