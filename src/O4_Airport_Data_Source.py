import bisect
import collections
import concurrent.futures
import functools
import glob
import json
import math
import numpy
import os
import pyproj
import re
import shapely.geometry
import shapely.ops
import shapely.prepared

import O4_File_Names as FNAMES
import O4_Config_Utils as CFG
import O4_Geo_Utils as GEO
from O4_Common_Types import IcaoCode

########################################################################################################################
#
# Hard-coded parameters
#
########################################################################################################################

__ZL_OPTIM_LIMIT__ = 12  # At which ZL do we stop replacing lower zl tiles with higher ones ?


class O4AirportDataSourceException(Exception):
    """Base exception class for all exceptions raised by this module"""
    pass


########################################################################################################################
#
# Zoom Level utility functions
#
########################################################################################################################

def zl_optimal_ground_dist(zl, screen_res, fov, fpa):
    """
    Problem: At the given fov/resolution/fpa, what is the applicable ground distance range of the given zl ?

    For ZL19, let's assume that zl_resolution = 0.2 meters/pixel (may vary with latitude, IIUC)
    In order words it's applicable to a screen resolution offering from 0 to 0.2 meters/pixel : after that, some pixels
    will just be discarded (down-sampled).
    >>> zl_to_mpx(19)
    0.2

    At which height will we get 0.2 meters/pixel, with the given fov/screen_res ?
    => height = (meters_per_pixel * screen_res) / (2 * tan(fov / 2))
    >>> '{:.15f}'.format(mpx_to_height(zl_to_mpx(19),
    ...                                math.radians(60),
    ...                                3840))
    '665.107510106448899'

    And at the given fpa, which ground distance do we need to get up there ?
    - ground_distance = height / tan(fpa)
    - ground_distance = ((meters_per_pixel * screen_res) / (2 * tan(fov / 2))) / tan(fpa)
    => ground_distance = (meters_per_pixel * screen_res) / (2 * tan(fov / 2) * tan(fpa))
    >>> '{:.15f}'.format(height_to_ground_dist(mpx_to_height(zl_to_mpx(19),
    ...                                                      math.radians(60),
    ...                                                      3840),
    ...                                        math.radians(7.5)))
    '5051.993105295444366'

    That's all this function does :
    >>> '{:.15f}'.format(zl_optimal_ground_dist(19, 3840, math.radians(60), math.radians(7.5)))
    '5051.993105295444366'
    """
    return height_to_ground_dist(zl_to_height(zl, screen_res, fov), fpa)


def zl_to_mpx(zl):
    """
    >>> list(map(zl_to_mpx, range(10, 22)))
    [102.4, 51.2, 25.6, 12.8, 6.4, 3.2, 1.6, 0.8, 0.4, 0.2, 0.1, 0.05]
    """
    return 0.1 * (2 ** (20 - zl))


def mpx_to_zl(mpx):
    """
    >>> tuple(map(mpx_to_zl, (0.04, 0.05, 0.06)))
    (21, 21, 20)
    >>> tuple(map(mpx_to_zl, (0.09, 0.10, 0.11)))
    (20, 20, 19)
    >>> tuple(map(mpx_to_zl, (0.19, 0.20, 0.21)))
    (19, 19, 18)
    >>> tuple(map(mpx_to_zl, (0.3, 0.4, 0.5)))
    (18, 18, 17)
    >>> tuple(map(mpx_to_zl, (0.7, 0.8, 0.9)))
    (17, 17, 16)
    >>> tuple(map(mpx_to_zl, (1.5, 1.6, 1.7)))
    (16, 16, 15)
    >>> tuple(map(mpx_to_zl, (3.1, 3.2, 3.3)))
    (15, 15, 14)
    >>> tuple(map(mpx_to_zl, (6.3, 6.4, 6.5)))
    (14, 14, 13)
    >>> tuple(map(mpx_to_zl, (12.7, 12.8, 12.9)))
    (13, 13, 12)
    >>> tuple(map(mpx_to_zl, (25.5, 25.6, 25.7)))
    (12, 12, 11)
    >>> tuple(map(mpx_to_zl, (51.1, 51.2, 51.3)))
    (11, 11, 10)
    >>> tuple(map(mpx_to_zl, (102.3, 102.4, 102.5)))
    (10, 10, 10)
    """
    zoom_levels = list(range(21, 9, -1))
    max_mpx_for_zl = list(map(zl_to_mpx, range(21, 10, -1)))
    return zoom_levels[bisect.bisect_left(max_mpx_for_zl, mpx)]


def height_to_visible_ground_dist(height, fov):
    """
    At the given height and fov, how much actual ground distance can we see ?
    => ground_distance = 2 * height * tan(fov / 2)

    >>> '{:.15f}'.format(height_to_visible_ground_dist(166, math.radians(60)))
    '191.680289370955734'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(332, math.radians(60)))
    '383.360578741911468'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(665, math.radians(60)))
    '767.875858022202237'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(1330, math.radians(60)))
    '1535.751716044404475'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(2660, math.radians(60)))
    '3071.503432088808950'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(5320, math.radians(60)))
    '6143.006864177617899'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(10641, math.radians(60)))
    '12287.168428893613964'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(21283, math.radians(60)))
    '24575.491558325607912'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(42566, math.radians(60)))
    '49150.983116651215823'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(85133, math.radians(60)))
    '98303.120933840807993'
    >>> '{:.15f}'.format(height_to_visible_ground_dist(170267, math.radians(60)))
    '196607.396568220021436'
    """
    return 2 * height * math.tan(fov / 2)


def visible_ground_dist_to_height(ground_dist, fov):
    """
    At which height will we see the desired ground distance, at the given fov ?
    => height = ground_distance / (2 * tan(fov / 2))
    """
    return ground_dist / (2 * math.tan(fov / 2))


def height_to_mpx(height, fov, screen_res):
    """
    At the given height/fov/screen_res, how many meters does each pixel represent ?
    => meters_per_pixel = 2 * height * tan(fov / 2) / screen_res

    >>> '{:.15f}'.format(height_to_mpx(166, math.radians(60), 3840))
    '0.049916742023686'
    >>> '{:.15f}'.format(height_to_mpx(332, math.radians(60), 3840))
    '0.099833484047373'
    >>> '{:.15f}'.format(height_to_mpx(665, math.radians(60), 3840))
    '0.199967671359949'
    >>> '{:.15f}'.format(height_to_mpx(1330, math.radians(60), 3840))
    '0.399935342719897'
    >>> '{:.15f}'.format(height_to_mpx(2660, math.radians(60), 3840))
    '0.799870685439794'
    >>> '{:.15f}'.format(height_to_mpx(5320, math.radians(60), 3840))
    '1.599741370879588'
    >>> '{:.15f}'.format(height_to_mpx(10641, math.radians(60), 3840))
    '3.199783445024379'
    >>> '{:.15f}'.format(height_to_mpx(21283, math.radians(60), 3840))
    '6.399867593313960'
    >>> '{:.15f}'.format(height_to_mpx(42566, math.radians(60), 3840))
    '12.799735186627920'
    >>> '{:.15f}'.format(height_to_mpx(85133, math.radians(60), 3840))
    '25.599771076521044'
    >>> '{:.15f}'.format(height_to_mpx(170267, math.radians(60), 3840))
    '51.199842856307299'
    """
    return height_to_visible_ground_dist(height, fov) / int(screen_res)


def mpx_to_height(mpx, fov, screen_res):
    """
    At which height will we get the desired meters/pixel, with the given fov/screen_res ?
    => height = (meters_per_pixel * screen_res) / (2 * tan(fov / 2))

    >>> '{:.15f}'.format(mpx_to_height(0.05, math.radians(60), 3840))
    '166.276877526612225'
    >>> '{:.15f}'.format(mpx_to_height(0.1, math.radians(60), 3840))
    '332.553755053224450'
    >>> '{:.15f}'.format(mpx_to_height(0.2, math.radians(60), 3840))
    '665.107510106448899'
    >>> '{:.15f}'.format(mpx_to_height(0.4, math.radians(60), 3840))
    '1330.215020212897798'
    >>> '{:.15f}'.format(mpx_to_height(0.8, math.radians(60), 3840))
    '2660.430040425795596'
    >>> '{:.15f}'.format(mpx_to_height(1.6, math.radians(60), 3840))
    '5320.860080851591192'
    >>> '{:.15f}'.format(mpx_to_height(3.2, math.radians(60), 3840))
    '10641.720161703182384'
    >>> '{:.15f}'.format(mpx_to_height(6.4, math.radians(60), 3840))
    '21283.440323406364769'
    >>> '{:.15f}'.format(mpx_to_height(12.8, math.radians(60), 3840))
    '42566.880646812729537'
    >>> '{:.15f}'.format(mpx_to_height(25.6, math.radians(60), 3840))
    '85133.761293625459075'
    >>> '{:.15f}'.format(mpx_to_height(51.2, math.radians(60), 3840))
    '170267.522587250918150'
    >>> '{:.15f}'.format(mpx_to_height(102.4, math.radians(60), 3840))
    '340535.045174501836300'
    """
    return visible_ground_dist_to_height(mpx * int(screen_res), fov)


def height_to_ground_dist(height, fpa):
    """
    With the given flight path angle, at which distance will we reach the given height :
    tan(fpa) = height / ground_distance
    => ground_distance = height / tan(fpa)
    """
    return height / math.tan(fpa)


def zl_to_height(zl, screen_res, fov):
    return mpx_to_height(zl_to_mpx(zl), fov, screen_res)


########################################################################################################################
#
# Data model : XPlaneTile, GoogleTile, Runway, Airport and AirportCollection
#
########################################################################################################################

class XPlaneTile:
    """Utility class to work with X-Plane tiles"""

    # We won't dynamically add any attribute : optimize RAM usage
    __slots__ = ['lat', 'lon', '_hash']

    def __init__(self, lat, lon):
        self.lat = int(math.floor(lat))
        self.lon = int(math.floor(lon))
        self._hash = hash((self.lat, self.lon))

    def __eq__(self, other):
        return (self.lat, self.lon) == (other.lat, other.lon) if isinstance(other, XPlaneTile) else NotImplemented

    def __lt__(self, other):
        return (self.lat, self.lon) < (other.lat, other.lon) if isinstance(other, XPlaneTile) else NotImplemented

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return '<XPlaneTile {:+03d}{:+04d}>'.format(self.lat, self.lon)

    def surrounding_tiles(self, include_self=False):
        """Return the tiles surrounding this one (NOT including itself).
        >>> [(tile.lat, tile.lon) for tile in XPlaneTile(43, 1).surrounding_tiles()]
        [(42, 0), (42, 1), (42, 2), (43, 0), (43, 2), (44, 0), (44, 1), (44, 2)]
        """
        return [tile
                # TODO: TileLatLon: there has to be a smarter way
                for lat_offset in [-1 if self.lat > -90 else 179, 0, 1 if self.lat < 90 else -179]
                for lon_offset in [-1 if self.lon > -90 else 179, 0, 1 if self.lon < 90 else -179]
                for tile in [XPlaneTile(self.lat + lat_offset,
                                        self.lon + lon_offset)]
                if tile != self or include_self]

    def polygon(self):
        return shapely.geometry.Polygon([(self.lon, self.lat),
                                         (self.lon + 1, self.lat),
                                         (self.lon + 1, self.lat + 1),
                                         (self.lon, self.lat + 1)])


class GTile:
    """Utility class to work with Google's zoomlevel-dependent tiles.
    See also :
    - O4_Geo_Utils.py
    - https://developers.google.com/maps/documentation/javascript/coordinates"""

    # We won't dynamically add any attribute : optimize RAM usage
    __slots__ = ['x', 'y', 'zl', '_hash']

    __INSTANCES_CACHE__ = {}
    __INSTANCES_CACHE_HITS__ = 0
    __INSTANCES_CACHE_MISSES__ = 0

    @classmethod
    def cache_info(cls):
        # LRU cache size tailored for heavy use case = Tile +42-089 (max airports), ZL 15 to 19
        return {'instances': 'hits={}, misses={}'.format(cls.__INSTANCES_CACHE_HITS__, cls.__INSTANCES_CACHE_MISSES__),
                'lower_zl_tile': str(cls.lower_zl_tile.cache_info()),
                'higher_zl_subtiles': str(cls.higher_zl_subtiles.cache_info()),
                'zl_siblings': str(cls.zl_siblings.cache_info()),
                '_cached_polygon': str(cls._cached_polygon.cache_info())}

    def __new__(cls, x, y, zl, *args, **kwargs):
        _id = (x, y, zl)

        if _id in cls.__INSTANCES_CACHE__:
            cls.__INSTANCES_CACHE_HITS__ += 1
            return cls.__INSTANCES_CACHE__[_id]

        cls.__INSTANCES_CACHE__[_id] = inst = super(GTile, cls).__new__(cls, *args, **kwargs)
        cls.__INSTANCES_CACHE_MISSES__ += 1
        return inst

    def __init__(self, x, y, zl):
        self.x = x
        self.y = y
        self.zl = zl
        self._hash = hash((self.x, self.y, self.zl))

    def __lt__(self, other):
        return (self.x, self.y, self.zl) < (other.x, other.y, other.zl) if isinstance(other, GTile) else NotImplemented

    def __eq__(self, other):
        return (self.x, self.y, self.zl) == (other.x, other.y, other.zl) if isinstance(other, GTile) else NotImplemented

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return '<GTile ({}, {})@ZL{}>'.format(self.x, self.y, self.zl)

    @functools.lru_cache(maxsize=2 ** 14)
    def lower_zl_tile(self, target_zl=None):
        if target_zl and target_zl >= self.zl:
            return self

        lower = GTile((((self.x // 16) // 2) * 16),
                      (((self.y // 16) // 2) * 16),
                      self.zl - 1)
        if target_zl and target_zl < self.zl - 1:
            # TODO: optim: should come up with some math instead
            return lower.lower_zl_tile(target_zl=target_zl)
        else:
            return lower

    @functools.lru_cache(maxsize=2 ** 13)
    def higher_zl_subtiles(self, target_zl=None):
        if target_zl and target_zl <= self.zl:
            return [self]

        zl = target_zl or (self.zl + 1)
        zl_diff = zl - self.zl
        return [GTile(x, y, zl)
                for x in range(self.x * 2 ** zl_diff, (self.x + 16) * 2 ** zl_diff, 16)
                for y in range(self.y * 2 ** zl_diff, (self.y + 16) * 2 ** zl_diff, 16)]

    @functools.lru_cache(maxsize=2 ** 13)
    def zl_siblings(self):
        return self.lower_zl_tile().higher_zl_subtiles()

    def surrounding_tiles(self, include_self=False):
        return [tile
                for x_offset in [-16, 0, 16]
                for y_offset in [-16, 0, 16]
                for tile in [GTile(self.x + x_offset,
                                   self.y + y_offset,
                                   self.zl)]
                if not (x_offset == 0 and y_offset == 0) or include_self]

    @staticmethod
    @functools.lru_cache(maxsize=2 ** 15)
    def _cached_polygon(x, y, zl):
        (lat_max, lon_min) = GEO.gtile_to_wgs84(x, y, zl)
        (lat_min, lon_max) = GEO.gtile_to_wgs84(x + 16, y + 16, zl)
        return shapely.geometry.Polygon([(lon_min, lat_min),
                                         (lon_max, lat_min),
                                         (lon_max, lat_max),
                                         (lon_min, lat_max)])

    def polygon(self):
        return self._cached_polygon(self.x, self.y, self.zl)


class Runway:
    """A particular runway of an Airport instance.

    Should be kept simple : its primary purpose is to hold some information about a runway,
    and to export itself to various formats : currently to json, and to a Shapely polygon.
    """

    # We won't dynamically add any attribute : optimize RAM usage
    __slots__ = ['width',
                 'end_1_id', 'end_1_lat', 'end_1_lon',
                 'end_2_id', 'end_2_lat', 'end_2_lon',
                 '_hash']

    def __init__(self, runway_data):
        self.width = runway_data['width']
        self.end_1_id = runway_data['end_1_id']
        self.end_1_lat = runway_data['end_1_lat']
        self.end_1_lon = runway_data['end_1_lon']
        self.end_2_id = runway_data['end_2_id']
        self.end_2_lat = runway_data['end_2_lat']
        self.end_2_lon = runway_data['end_2_lon']
        self._hash = (self.end_1_id, self.end_2_id)

    def __repr__(self):
        return '<Runway: {} / {}>'.format(self.end_1_id, self.end_2_id)

    def __eq__(self, other):
        if not isinstance(other, Runway):
            return NotImplemented
        return self.end_1_id == other.end_1_id and self.end_2_id == other.end_2_id

    def __hash__(self):
        return self._hash

    def to_json(self):
        return {
            'width': self.width,
            'end_1_id': self.end_1_id,
            'end_1_lat': self.end_1_lat,
            'end_1_lon': self.end_1_lon,
            'end_2_id': self.end_2_id,
            'end_2_lat': self.end_2_lat,
            'end_2_lon': self.end_2_lon
        }

    def relevant_xp_tiles(self, include_surrounding_tiles=False):
        """Return the tiles where this runway is located (could be several ones)."""
        return [tile
                for end_tile in {XPlaneTile(self.end_1_lat, self.end_1_lon),
                                 XPlaneTile(self.end_2_lat, self.end_2_lon)}
                for tile in [end_tile] + (end_tile.surrounding_tiles() if include_surrounding_tiles else [])]

    def _runway_center(self):
        geod = pyproj.Geod(ellps='WGS84')

        # First compute the azimuts and length between the two runway ends
        (azimut_1_2, azimut_2_1, length) = geod.inv(lons1=self.end_1_lon,
                                                    lats1=self.end_1_lat,
                                                    lons2=self.end_2_lon,
                                                    lats2=self.end_2_lat)

        # Then find the center of the runway and return it
        (lon, lat, _) = geod.fwd(lons=self.end_1_lon,
                                 lats=self.end_1_lat,
                                 az=azimut_1_2,
                                 dist=length / 2)

        return shapely.geometry.Point(lon, lat)

    def raw_polygon(self, zl, screen_res, fov, fpa):
        """Return a Shapely polygon for the given combination of zl, screen_res, fov and fpa (see
        the docstring of zl_optimal_ground_dist() for a detailed explanation, with self-tests.
        The final polygon will be a rectangle of optimal_dist by optimal_dist/2
        """

        geod = pyproj.Geod(ellps='WGS84')
        optimal_ground_dist = zl_optimal_ground_dist(zl, screen_res, math.radians(fov), math.radians(fpa))
        coords = []

        # First compute the azimuts and length between the two runway ends
        (azimut_1_2, azimut_2_1, length) = geod.inv(lons1=self.end_1_lon,
                                                    lats1=self.end_1_lat,
                                                    lons2=self.end_2_lon,
                                                    lats2=self.end_2_lat)

        # Deduce the polygon dimensions
        polygon_length = 2 * optimal_ground_dist + length
        polygon_width = (optimal_ground_dist + self.width) / 1.61803398875
        center = self._runway_center()

        # Compute the two points near end_1
        (lon, lat, _) = geod.fwd(lons=center.x,
                                 lats=center.y,
                                 az=azimut_2_1,
                                 dist=polygon_length / 2)
        ((lon_1, lon_2), (lat_1, lat_2), _) = geod.fwd(lons=(lon, lon),
                                                       lats=(lat, lat),
                                                       az=(azimut_2_1 - 90.0,
                                                           azimut_2_1 + 90.0),
                                                       dist=(polygon_width / 2,
                                                             polygon_width / 2))
        coords.append((lon_1, lat_1))
        coords.append((lon_2, lat_2))

        # Then the two points near end_2
        ((lon_1, lon_2), (lat_1, lat_2), _) = geod.fwd(lons=(lon_1, lon_2),
                                                       lats=(lat_1, lat_2),
                                                       az=(azimut_1_2,
                                                           azimut_1_2),
                                                       dist=(polygon_length, polygon_length))
        coords.append((lon_2, lat_2))
        coords.append((lon_1, lat_1))

        return shapely.geometry.Polygon(coords)

    def gtiles(self, zl, screen_res, fov, fpa):
        # First compute the initial polygon, and prepare it for possibly massive querying
        prepared_polygon = shapely.prepared.prep(self.raw_polygon(zl, screen_res, fov, fpa))

        # Find all the gtiles covering it
        (lon_min, lat_min, lon_max, lat_max) = prepared_polygon.context.envelope.bounds
        x_min, y_min = GEO.wgs84_to_orthogrid(lat_max, lon_min, zl)
        x_max, y_max = GEO.wgs84_to_orthogrid(lat_min, lon_max, zl)

        return filter(lambda tile: prepared_polygon.intersects(tile.polygon()),
                      (GTile(x, y, zl)
                       for x in range(x_min, x_max + 16, 16)
                       for y in range(y_min, y_max + 16, 16)))


class Airport:
    """A particular airport of an AirportCollection instance.

    Should be kept simple : its primary purpose is to hold some information about an airport,
    and to export itself to various formats : currently to json, and to a list of Shapely polygons.

    Runway information are stored in children instances of the Runway class.
    """

    # We won't dynamically add any attribute : optimize RAM usage
    __slots__ = ['type', 'icao', 'name', 'elevation', 'runways']

    def __init__(self, airport_data):
        self.type = airport_data['type']
        self.icao = IcaoCode(airport_data['icao'])
        self.name = airport_data['name']
        self.elevation = airport_data['elevation']
        self.runways = {(rw.end_1_id, rw.end_2_id): rw
                        for rw in [Runway(rw_data) for rw_data in airport_data['runways']]}

    def __repr__(self):
        return '<Airport: {} "{}">'.format(self.icao, self.name)

    #
    # Partial Dict interface
    #

    def __getitem__(self, key):
        return self.runways[key]

    def __setitem__(self, key, value):
        self.runways[key] = value

    def keys(self):
        return self.runways.keys()

    def values(self):
        return self.runways.values()

    def items(self):
        return self.runways.items()

    def setdefault(self, key, default):
        return self.runways.setdefault(key, default)

    #
    # Airport Interface
    #

    def to_json(self):
        return {
            'type': self.type,
            'icao': str(self.icao),
            'name': self.name,
            'elevation': self.elevation,
            'runways': [rw.to_json() for rw in self.runways.values()]
        }

    def gtiles(self, zl, screen_res, fov, fpa):
        return set([tile
                    for rw in self.runways.values()
                    for tile in rw.gtiles(zl, screen_res, fov, fpa)])


class AirportCollection:
    """A collection of Airport instances.

    Should be kept simple : its primary purpose is to aggregate and manage several Airports, work
    with other AirportCollections, and facilitate exporting a group of airports to various formats.

    The constructor accepts :
    - a single Airport instance
    - another AirportCollection instance
    - a list of Airport instances
    - a list of AirportCollection instances
    - a dict of {key: airport_sub_dict}, typically coming from JSON data
        => key is ignored, aiport_sub_dict is turned in an Airport instance)
    """

    @classmethod
    def cache_info(cls):
        return {'gtiles': str(cls.gtiles.cache_info())}

    def __init__(self, xp_tile, include_surrounding_tiles=False):
        self.xp_tile = xp_tile
        self.airports = {arpt.icao: arpt
                         for arpt in AirportDataSource.airports_in(xp_tile,
                                                                   include_surrounding_tiles=include_surrounding_tiles)}

    #
    # Partial Dict interface
    #

    def __getitem__(self, key):
        return self.airports[key]

    def __setitem__(self, key, value):
        self.airports[key] = value

    def keys(self):
        return self.airports.keys()

    def values(self):
        return self.airports.values()

    def items(self):
        return self.airports.items()

    def setdefault(self, key, default):
        return self.airports.setdefault(key, default)

    #
    # gtiles utilities
    #

    @staticmethod
    def _margin_width(zl, fraction):
        lat_1, lon_1 = GEO.gtile_to_wgs84(0, 0, zl)
        lat_2, lon_2 = GEO.gtile_to_wgs84(int(16 / fraction), 0, zl)
        return shapely.geometry.Point(lon_1, lat_1).distance(shapely.geometry.Point(lon_2, lat_2))

    def _tile_margin_poly(self, zl, greediness):
        margin_width = self._margin_width(max(__ZL_OPTIM_LIMIT__, (zl - greediness)), 1)
        tile_poly = self.xp_tile.polygon()
        margin_poly = tile_poly.exterior.buffer(distance=margin_width,
                                                cap_style=shapely.geometry.CAP_STYLE.square,
                                                join_style=shapely.geometry.JOIN_STYLE.mitre)
        return shapely.prepared.prep(margin_poly.union(tile_poly))

    def _sub_zl_margin_set(self, zl, sub_zl_gtiles):
        """Take a margin, 1 ZLn tile wide, around each ZLn+1 polygon. Return the corresponding ZLn tiles."""
        margin_tiles = set()
        for zl_n1_polygon in self.as_polygons(sub_zl_gtiles):
            # Build the margin polygon :
            # - exterior: parallel to ZLn+1 exterior, at margin_width distance
            # - interior: ZLn+1 exterior
            zl_n_margin = zl_n1_polygon.exterior.buffer(distance=self._margin_width(zl, 16),
                                                        cap_style=shapely.geometry.CAP_STYLE.square,
                                                        join_style=shapely.geometry.JOIN_STYLE.mitre)

            # Prepare the margin polygon for multiple querying
            margin_polygon = shapely.prepared.prep(zl_n_margin.difference(zl_n1_polygon))

            # Find all the ZLn gtiles covering the ZLn+1 polygon + margin
            (lon_min, lat_min, lon_max, lat_max) = margin_polygon.context.envelope.bounds
            x_min, y_min = GEO.wgs84_to_orthogrid(lat_max, lon_min, zl)
            x_max, y_max = GEO.wgs84_to_orthogrid(lat_min, lon_max, zl)

            # Only keep the ZLn tiles intersecting the margin polygon
            margin_tiles.update([t for t in [GTile(x, y, zl)
                                             for x in range(x_min, x_max + 16, 16)
                                             for y in range(y_min, y_max + 16, 16)]
                                 if margin_polygon.intersects(t.polygon())])
        return margin_tiles

    @staticmethod
    def _optimized_tile_set(tiles: set, zl, greediness, greediness_threshold):
        # Group the input tiles by their lower ZL tile (in a dict of {ZLn-1: [ZLn]})
        zl_n_tiles = collections.defaultdict(list)
        for tile in tiles:
            zl_n_tiles[tile.lower_zl_tile()].append(tile)

        # For each ZL from ZLn-1 up to ZLmin, check if it's already 70% covered by ZLn tiles
        # Note that if ZLn <= ZLmin, then this loop will be skipped
        zl_optim_limit = max(__ZL_OPTIM_LIMIT__, (zl - greediness))
        for threshold_len in [greediness_threshold * 2 ** (2 * (zl - i))
                              for i in range(zl - 1, zl_optim_limit - 1, -1)]:
            for zl_optim_tile in zl_n_tiles.keys():
                if len(zl_n_tiles[zl_optim_tile]) >= threshold_len:
                    # If so, add the remaining ZLn tiles
                    zl_n_tiles[zl_optim_tile] = zl_optim_tile.higher_zl_subtiles(target_zl=zl)

            # Prepare a new dict for the next iteration, reuse the existing tiles
            zl_n_tiles_new = collections.defaultdict(list)
            for (zl_optim_tile, zl_n_group) in zl_n_tiles.items():
                zl_n_tiles_new[zl_optim_tile.lower_zl_tile()].extend(zl_n_group)
            zl_n_tiles = zl_n_tiles_new

        return set([tile
                    for tile_group in zl_n_tiles.values()
                    for tile in tile_group])

    @staticmethod
    def _compacted_tile_set(tiles: set):
        """Compact the tiles into as few instances as possible, by replacing a group of ZLn tiles with their common
        ZLn-1 tile, if all the ZLn tiles of the group are present."""
        current_tiles = tiles
        previous_tiles = set()
        # Repeat the process until a full iteration went without changing anything (meaning: until we're done)
        while current_tiles != previous_tiles:
            previous_tiles = current_tiles
            current_tiles = set()
            rejected_tiles = set()
            # Iterate through each tile, to see if something can be optimized
            for tile in previous_tiles:
                if tile in rejected_tiles:
                    # A sibling detected that this one is superseded by its lower_zl tile : ignore it
                    pass
                else:
                    siblings = set(tile.zl_siblings())
                    if len(siblings.intersection(previous_tiles)) == 4:
                        # They're already all in : add their common lower zl tile
                        current_tiles.add(tile.lower_zl_tile())
                        # Re-add them so they are kept
                        current_tiles.update(siblings)
                        # Optim: mark them as 'rejected', so the siblings are just skipped
                        rejected_tiles.update(siblings)
                    else:
                        # Nothing wrong with this one : add it as-is
                        current_tiles.add(tile)
        return current_tiles

    #
    # Airport Interface
    #

    @functools.lru_cache(maxsize=2 ** 3)
    def gtiles(self, zl, cover_zl, screen_res, fov, fpa, greediness, greediness_threshold, xp_tile_filter):
        """Return the ZL gtiles needed to cover this airport collection.
        This list ALSO includes all the (interior) higher ZL sub-tiles, down to cover_zl"""

        # First compute the tiles for the current zl
        tile_margin_poly = self._tile_margin_poly(zl, greediness)
        selected_airports = filter(lambda a: zl <= cover_zl.max_cover_zl_for(a.icao),
                                   self.airports.values())
        gtiles = functools.reduce(lambda s1, s2: s1.union(s2),
                                  map(lambda a: set(filter(lambda t: not tile_margin_poly.disjoint(t.polygon()),
                                                           a.gtiles(zl, screen_res, fov, fpa))),
                                      selected_airports))

        if zl < cover_zl.max:
            # If we're not at ZLmax, compute the ZLn+1 gtiles, and "compact" them
            # When compacted, this list will then also include any ZLn gtiles that were fully covered by ZLn+1 gtiles
            # We'll then exclude any such ZLn tile from the final list, thus creating "holes" for the ZLn+1 gtiles
            all_sub_gtiles = set(self.gtiles(zl=zl + 1,
                                             cover_zl=cover_zl,
                                             screen_res=screen_res,
                                             fov=fov,
                                             fpa=fpa,
                                             greediness=greediness,
                                             greediness_threshold=greediness_threshold,
                                             xp_tile_filter=False))
            compacted_sub_gtiles = self._compacted_tile_set(all_sub_gtiles)
        else:
            all_sub_gtiles = set()
            compacted_sub_gtiles = set()

        # Take a margin around each of the ZLn+1 polygons, and add the corresponding ZLn gtiles
        # We need this margin to ensure that the zones are progressive, to prevent jumps from ZLn to ZLn+2.
        if all_sub_gtiles:
            gtiles.update(self._sub_zl_margin_set(zl, all_sub_gtiles))

        # Optimize texture usage, but "eating" up any lower zl being "greediness_threshold"-percent covered by this zl
        # Will look up to 'greediness' lower levels
        optimized_gtiles = self._optimized_tile_set(gtiles, zl, greediness, greediness_threshold)

        # Only keep useful ZLn gtiles : remove the gtiles that are fully covered by ZLn+1
        #                             : also remove those outside the xp_tile border (with a margin)
        own_zl_gtiles = set(filter(lambda t: not tile_margin_poly.disjoint(t.polygon()),
                                   optimized_gtiles - compacted_sub_gtiles))

        # Finally, return the remaining ZLn tiles + all the previously computed ZLn+1..ZLmax subtiles
        final_gtiles = own_zl_gtiles.union(all_sub_gtiles)
        if xp_tile_filter:
            tile_poly = shapely.prepared.prep(self.xp_tile.polygon())
            return set(filter(lambda t: not tile_poly.disjoint(t.polygon()),
                              final_gtiles))
        return final_gtiles

    @staticmethod
    def as_polygons(gtiles):
        """Return as few Shapely polygons as possible for the given gtiles."""
        polys = shapely.ops.unary_union([gtile.polygon() for gtile in gtiles])

        if isinstance(polys, shapely.geometry.MultiPolygon):
            return list(polys)
        elif isinstance(polys, shapely.geometry.Polygon):
            return [polys]
        elif isinstance(polys, list):
            return polys
        else:
            return polys

    def zone_list(self, screen_res, fov, fpa, provider, base_zl, cover_zl, greediness, greediness_threshold):
        tile_zones = []
        for zl in range(cover_zl.max, base_zl - 1, -1):
            for polygon in self.as_polygons(self.gtiles(zl=zl,
                                                        cover_zl=cover_zl,
                                                        screen_res=screen_res,
                                                        fov=fov,
                                                        fpa=fpa,
                                                        greediness=greediness,
                                                        greediness_threshold=greediness_threshold,
                                                        xp_tile_filter=True)):
                coords = []
                for (x, y) in polygon.exterior.coords:
                    coords.extend([y, x])
                tile_zones.append([coords, zl, provider])
        return tile_zones

    def disk_size(self, zl, cover_zl, screen_res, fov, fpa, greediness, greediness_threshold):
        # This could be computed more precisely, but each DDS texture has a fixed size of 11,184,952 bytes, whatever
        # the zoom level.
        # Since we only need a (fast) estimate, just multiply that constant with the number of tiles
        return 11184952 * len(self.gtiles(zl=zl,
                                          cover_zl=cover_zl,
                                          screen_res=screen_res,
                                          fov=fov,
                                          fpa=fpa,
                                          greediness=greediness,
                                          greediness_threshold=greediness_threshold,
                                          xp_tile_filter=True))


########################################################################################################################
#
# Data Source parsers
#
########################################################################################################################


class OSMAirportsParser:
    """Not yet implemented"""

    def parse(self, *tiles):
        raise NotImplementedError


class XPlaneAptDatParser:
    """X-Plane apt.dat parser.

    This is not a fully-compliant apt.dat parser yet : it only reads data relevant to runways.

    It is compliant with the relevant subset of both XP-APT1100-Spec and the older XP-APT1050-Spec:
    - http://developer.x-plane.com/wp-content/uploads/2018/02/XP-APT1100-Spec_revised_02142018.pdf
    - http://developer.x-plane.com/wp-content/uploads/2017/02/XP-APT1050-Spec.pdf
    """
    # A few regexes to extract relevant information from an X-Plane apt.dat files
    __RE_ARPT__ = re.compile(r'\s+'.join([r'^(?P<airport_type>1|16|17)',
                                          r'(?P<airport_elevation>\S+)',
                                          r'(?P<airport_deprecated_1>\S+)',
                                          r'(?P<airport_deprecated_2>\S+)',
                                          r'(?P<airport_ICAO>\S+)',
                                          r'(?P<airport_name>.*)']))

    __RE_IS_RWY__ = re.compile(r'^10[012]\s+')

    __RE_LAND_RWY__ = re.compile(r'\s+'.join([r'^100',
                                              r'(?P<runway_width>\S+)',
                                              r'(?P<runway_surface>\S+)',
                                              r'(?P<runway_shoulder_surface>\S+)',
                                              r'(?P<runway_smoothness>\S+)',
                                              r'(?P<runway_centerline_lights>\S+)',
                                              r'(?P<runway_edge_lights>\S+)',
                                              r'(?P<runway_distance_signs>\S+)',
                                              r'(?P<runway_end_1_number>\S+)',
                                              r'(?P<runway_end_1_latitude>\S+)',
                                              r'(?P<runway_end_1_longitude>\S+)',
                                              r'(?P<runway_end_1_displaced_threshold_length>\S+)',
                                              r'(?P<runway_end_1_blastpad_length>\S+)',
                                              r'(?P<runway_end_1_markings>\S+)',
                                              r'(?P<runway_end_1_approach_lights>\S+)',
                                              r'(?P<runway_end_1_touchdown_lights>\S+)',
                                              r'(?P<runway_end_1_id_lights>\S+)',
                                              r'(?P<runway_end_2_number>\S+)',
                                              r'(?P<runway_end_2_latitude>\S+)',
                                              r'(?P<runway_end_2_longitude>\S+)',
                                              r'(?P<runway_end_2_displaced_threshold_length>\S+)',
                                              r'(?P<runway_end_2_blastpad_length>\S+)',
                                              r'(?P<runway_end_2_markings>\S+)',
                                              r'(?P<runway_end_2_approach_lights>\S+)',
                                              r'(?P<runway_end_2_touchdown_lights>\S+)',
                                              r'(?P<runway_end_2_id_lights>\S+)']))

    __RE_WATER_RWY__ = re.compile(r'\s+'.join(['^101',
                                               r'(?P<waterway_width>\S+)',
                                               r'(?P<waterway_buoys>\S+)',
                                               r'(?P<waterway_end_1_number>\S+)',
                                               r'(?P<waterway_end_1_latitude>\S+)',
                                               r'(?P<waterway_end_1_longitude>\S+)',
                                               r'(?P<waterway_end_2_number>\S+)',
                                               r'(?P<waterway_end_2_latitude>\S+)',
                                               r'(?P<waterway_end_2_longitude>\S+)']))

    __RE_HELIPAD__ = re.compile(r'\s+'.join([r'^102',
                                             r'(?P<helipad_designator>\S+)',
                                             r'(?P<helipad_center_latitude>\S+)',
                                             r'(?P<helipad_center_longitude>\S+)',
                                             r'(?P<helipad_orientation>\S+)',
                                             r'(?P<helipad_length>\S+)',
                                             r'(?P<helipad_width>\S+)',
                                             r'(?P<helipad_surface>\S+)',
                                             r'(?P<helipad_markings>\S+)',
                                             r'(?P<helipad_shoulder_surface>\S+)',
                                             r'(?P<helipad_smoothness>\S+)',
                                             r'(?P<helipad_edge_lights>\S+)']))

    @staticmethod
    def apt_dat_files():
        """Return the list of all the apt.dat files within the given X-Plane installation.
        The order is important : airports in the first files will be overwritten by those in the last ones (as in XP)"""
        xp_dir = CFG.xplane_install_dir
        apt_dat = os.path.join('Earth nav data', 'apt.dat')
        default_scenery = os.path.join(xp_dir, 'Resources', 'default scenery', 'default apt dat', apt_dat)
        global_airports = os.path.join(xp_dir, 'Custom Scenery', 'Global Airports', apt_dat)
        custom_airports = set(glob.glob(os.path.join(xp_dir, 'Custom Scenery', '*', apt_dat))) - {global_airports}
        return [default_scenery, global_airports] + sorted(custom_airports)

    @staticmethod
    def parse(apt_dat_file):
        # Translation dicts
        airport_types = {'1': 'airport', '16': 'seaplane_base', '17': 'heliport'}

        with open(apt_dat_file, encoding='latin9') as apt_dat:
            # Group the source lines by airport
            current_airport_data = None
            for src_line in apt_dat:
                m = XPlaneAptDatParser.__RE_ARPT__.match(src_line)
                if m:
                    new_airport_data = {
                        'type': airport_types[m.group('airport_type')],
                        'icao': IcaoCode(m.group('airport_ICAO')),
                        'name': m.group('airport_name'),
                        'elevation': m.group('airport_elevation'),
                        'runways': list()
                    }
                    if current_airport_data is None:
                        # First airport : start collecting its runways
                        current_airport_data = new_airport_data
                    else:
                        # New airport : yield the current one and its runways
                        yield Airport(current_airport_data)
                        # Start collecting the runways for this new airport
                        current_airport_data = new_airport_data

                elif XPlaneAptDatParser.__RE_IS_RWY__.match(src_line):
                    # TODO: XPlaneAptDatParser: also parse seaplane bases et heliports
                    m = XPlaneAptDatParser.__RE_LAND_RWY__.match(src_line)
                    if m and current_airport_data is not None:
                        current_airport_data['runways'].append({
                            'end_1_id': m.group('runway_end_1_number'),
                            'end_1_lat': numpy.float(m.group('runway_end_1_latitude')),
                            'end_1_lon': numpy.float(m.group('runway_end_1_longitude')),
                            'end_2_id': m.group('runway_end_2_number'),
                            'end_2_lat': numpy.float(m.group('runway_end_2_latitude')),
                            'end_2_lon': numpy.float(m.group('runway_end_2_longitude')),
                            'width': numpy.float(m.group('runway_width'))})
                else:
                    pass  # skip any other line


########################################################################################################################
#
# Main class of this module : AirportDataSource
#
########################################################################################################################

class AirportDataSource:
    """Represents a source of airport data (be it X-Plane apt.dat files, OSM data, or whatever other service).

    Should be kept generic, to support multiple sources without having to change the callers too much (if at all).
    In this respect, it should only work with instances of AirportCollection, Airport and Runway.

    It transparently caches parsed data to the filesystem, in a tree of JSON files, and to a lesser extent in memory.

    The actual parsing work is done by specialized sister classes.
    Only XPlaneAptDatParser is implemented for now, but an OSM parser should probably come next.
    """

    __CACHE_FORMAT_VERSION__ = 0
    __PARSER_CLASSES__ = [XPlaneAptDatParser]  # [OSMAirportsParser, XPlaneAptDatParser]
    __TILE_AIRPORTS__ = dict()
    _cache_update_pool = None
    _cache_updater_main_job = None
    _cache_updater_tile_jobs = None

    @classmethod
    def airports_in(cls, xp_tile, include_surrounding_tiles=False):
        """Return an AirportCollection of all the airports in the given tile(s)."""

        # Optionally add the surrounding tiles to the search range
        search_range = {xp_tile}
        if include_surrounding_tiles:
            search_range.update(xp_tile.surrounding_tiles())

        # Load the airport data from the filesystem cache (check if already loaded first)
        for t in filter(lambda x: x not in cls.__TILE_AIRPORTS__, search_range):
            cls.__TILE_AIRPORTS__[t] = cls._read_cached_tile(t)

        # Now we should have all the tiles loaded, return the corresponding airports
        return {a
                for t in search_range
                for a in cls.__TILE_AIRPORTS__[t]}

    @classmethod
    def _read_cached_tile(cls, tile):
        cache_was_rebuilt = False

        # Ensure the tile cache file has been built : first waits for the main job to parse the apt.dat.
        # We need that because the tile updater jobs won't be started until that part is done.
        if cls._cache_updater_main_job is not None and cls._cache_updater_main_job.running():
            cache_was_rebuilt = True
            concurrent.futures.wait([cls._cache_updater_main_job])

        # If we don't have an updater job for this tile, then it means there wasn't any airport data for it,
        # just return an empty collection
        if cls._cache_updater_tile_jobs is not None and tile not in cls._cache_updater_tile_jobs:
            return []

        if cls.cache_update_in_progress():
            cache_was_rebuilt = True
            concurrent.futures.wait([cls._cache_updater_tile_jobs[tile]])

        tile_cache_file = FNAMES.cached_arpt_data(lat=tile.lat, lon=tile.lon)

        if not os.path.exists(tile_cache_file):
            if cache_was_rebuilt:
                raise O4AirportDataSourceException("Couldn't find {}, please rebuild the cache manually, "
                                                   "or restart Ortho4XP".format(tile_cache_file))
            else:
                # If we don't have that tile, and no cache update was triggered this turn, then it means we don't have
                # any airport data for it, just return an empty collection
                return []

        with open(tile_cache_file) as f:
            return [Airport(a) for a in json.load(f).values()]

    @staticmethod
    def _parse_apt_dat(_apt_dat_file):
        apt_dat_parser = XPlaneAptDatParser()
        _apt_data = collections.defaultdict(dict)
        for _arpt in apt_dat_parser.parse(_apt_dat_file):
            for _rw in _arpt.values():
                for _t in _rw.relevant_xp_tiles(include_surrounding_tiles=False):
                    if _arpt.icao not in _apt_data[_t].keys():
                        _apt_data[_t][_arpt.icao] = _arpt
        return _apt_data

    @staticmethod
    def _write_tile_cache(tile, airports_dict):
        tile_cache_file = FNAMES.cached_arpt_data(lat=tile.lat, lon=tile.lon)
        os.makedirs(os.path.dirname(tile_cache_file), exist_ok=True)
        with open(tile_cache_file, 'w') as f:
            # See https://bugs.python.org/issue12134, it's a lot faster to first dump to a json string, and only then
            # writing it as a whole, instead of just calling json.dump()
            f.write(json.dumps({str(icao): arpt.to_json()
                                for (icao, arpt) in airports_dict.items()},
                               sort_keys=True,
                               indent=True))

    @classmethod
    def _main_updater_job(cls, apt_dat_files):
        # First parse all the apt.dat files available
        # This part will block until we're done (but this function is also running in a thread)
        parsed_airport_data = collections.defaultdict(dict)
        for apt_data in [cls._cache_update_pool.submit(cls._parse_apt_dat, apt_file) for apt_file in apt_dat_files]:
            for (tile, airport_collection) in apt_data.result().items():
                for (icao, airport) in airport_collection.items():
                    # Intentionally overwrite global airport data with custom scenery ones
                    parsed_airport_data[tile][icao] = airport

        # Then start writing the tile cache files in the background
        cls._cache_updater_tile_jobs = {tile: cls._cache_update_pool.submit(cls._write_tile_cache,
                                                                            tile,
                                                                            airports_dict)
                                        for (tile, airports_dict) in parsed_airport_data.items()}

        # Finally, rewrite the cache info file
        with open(os.path.join(FNAMES.Airport_dir, 'cache_info.json'), 'w') as f:
            f.write(json.dumps({'cache_format_ver': cls.__CACHE_FORMAT_VERSION__,
                                'apt_dat_files': {apt_dat: {'mtime': os.path.getmtime(apt_dat)}
                                                  for apt_dat in apt_dat_files}},
                               sort_keys=True,
                               indent=True))

    @classmethod
    def apt_dat_files(cls):
        """Compare the current list of apt.dat files against what we used last time.
        If any of the apt.dat file were changed/added/removed, then return the new list.
        Otherwise, just return an empty list so that cache rebuilding is skipped."""
        cache_info_file = os.path.join(FNAMES.Airport_dir, 'cache_info.json')

        if not os.path.exists(cache_info_file):
            return XPlaneAptDatParser.apt_dat_files()

        with open(cache_info_file) as f:
            cache_info = json.load(f)

        apt_dat_files = XPlaneAptDatParser.apt_dat_files()

        if cache_info['cache_format_ver'] != cls.__CACHE_FORMAT_VERSION__:
            return apt_dat_files

        if set(apt_dat_files) != set(cache_info['apt_dat_files']):
            return apt_dat_files

        for apt_dat in apt_dat_files:
            if os.path.getmtime(apt_dat) != cache_info['apt_dat_files'][apt_dat]['mtime']:
                return apt_dat_files

        return list()

    @classmethod
    def wait_for_cache_update(cls):
        # Just waits for all the other updater jobs to complete
        concurrent.futures.wait([cls._cache_updater_main_job])
        if cls.cache_update_in_progress():
            concurrent.futures.wait(list(cls._cache_updater_tile_jobs.values()))

    @classmethod
    def cache_update_in_progress(cls):
        return ((cls._cache_updater_main_job is not None and
                 cls._cache_updater_main_job.running()) or
                (cls._cache_updater_tile_jobs is not None and
                 any([j.running() for j in cls._cache_updater_tile_jobs.values()])))

    @classmethod
    def update_cache(cls, force_rebuild=False):
        if force_rebuild:
            os.remove(os.path.join(FNAMES.Airport_dir, 'cache_info.json'))

        apt_dat_files = cls.apt_dat_files()
        if apt_dat_files:
            cls._cache_update_pool = cls._cache_update_pool or concurrent.futures.ThreadPoolExecutor()
            cls._cache_updater_main_job = cls._cache_update_pool.submit(cls._main_updater_job, apt_dat_files)
