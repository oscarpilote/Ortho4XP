import bisect
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
    >>> list(map(zl_to_mpx, range(10, 20)))
    [102.4, 51.2, 25.6, 12.8, 6.4, 3.2, 1.6, 0.8, 0.4, 0.2]
    """
    return 0.2 * (2 ** (19 - zl))


def mpx_to_zl(mpx):
    """
    >>> tuple(map(mpx_to_zl, (0.1, 0.2, 0.3)))
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
    zoom_levels = list(range(19, 9, -1))
    max_mpx_for_zl = list(map(zl_to_mpx, range(19, 10, -1)))
    return zoom_levels[bisect.bisect_left(max_mpx_for_zl, mpx)]


def height_to_visible_ground_dist(height, fov):
    """
    At the given height and fov, how much actual ground distance can we see ?
    => ground_distance = 2 * height * tan(fov / 2)

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
    return height_to_visible_ground_dist(height, fov) / screen_res


def mpx_to_height(mpx, fov, screen_res):
    """
    At which height will we get the desired meters/pixel, with the given fov/screen_res ?
    => height = (meters_per_pixel * screen_res) / (2 * tan(fov / 2))

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
    return visible_ground_dist_to_height(mpx * screen_res, fov)


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
    __slots__ = ['lat', 'lon']

    def __init__(self, lat, lon):
        self.lat = int(math.floor(lat))
        self.lon = int(math.floor(lon))

    def __eq__(self, other):
        return (self.lat, self.lon) == (other.lat, other.lon) if isinstance(other, XPlaneTile) else NotImplemented

    def __lt__(self, other):
        return (self.lat, self.lon) < (other.lat, other.lon) if isinstance(other, XPlaneTile) else NotImplemented

    def __hash__(self):
        return hash((self.lat, self.lon))

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

    @classmethod
    def from_lat_lon(cls, lat, lon, zl):
        (x, y) = GEO.wgs84_to_orthogrid(lat, lon, zl)
        return GTile(x, y, zl)

    def __init__(self, x, y, zl):
        self.x = x
        self.y = y
        self.zl = zl

    def __lt__(self, other):
        return (self.x, self.y, self.zl) < (other.x, other.y, other.zl) if isinstance(other, GTile) else NotImplemented

    def __eq__(self, other):
        return (self.x, self.y, self.zl) == (other.x, other.y, other.zl) if isinstance(other, GTile) else NotImplemented

    def __hash__(self):
        return hash((self.x, self.y, self.zl))

    def __repr__(self):
        return '<GTile ({}, {})@ZL{}>'.format(self.x, self.y, self.zl)

    def lower_zl_tile(self, target_zl=None):
        if target_zl and target_zl >= self.zl:
            return self

        lower = GTile((((self.x // 16) // 2) * 16),
                      (((self.y // 16) // 2) * 16),
                      self.zl - 1)
        if target_zl and target_zl < self.zl - 1:
            return lower.lower_zl_tile(target_zl=target_zl)
        else:
            return lower

    def higher_zl_subtiles(self, target_zl=None):
        if target_zl and target_zl <= self.zl:
            return [self]

        zl_diff = (target_zl - self.zl) if target_zl else 1
        return {GTile(x, y, target_zl or (self.zl + 1))
                for x in range(self.x * 2 ** zl_diff, (self.x + 16) * 2 ** zl_diff, 16)
                for y in range(self.y * 2 ** zl_diff, (self.y + 16) * 2 ** zl_diff, 16)}

    def zl_siblings(self, include_self=False):
        return self.lower_zl_tile().higher_zl_subtiles() - (set() if include_self else {self})

    def surrounding_tiles(self, include_self=False):
        return [tile
                for x_offset in [-16, 0, 16]
                for y_offset in [-16, 0, 16]
                for tile in [GTile(self.x + x_offset,
                                   self.y + y_offset,
                                   self.zl)]
                if tile != self or include_self]

    def polygon(self):
        (lat_max, lon_min) = GEO.gtile_to_wgs84(self.x, self.y, self.zl)
        (lat_min, lon_max) = GEO.gtile_to_wgs84(self.x + 16, self.y + 16, self.zl)
        return shapely.geometry.Polygon([(lon_min, lat_min),
                                         (lon_max, lat_min),
                                         (lon_max, lat_max),
                                         (lon_min, lat_max)])


class Runway:
    """A particular runway of an Airport instance.

    Should be kept simple : its primary purpose is to hold some information about a runway,
    and to export itself to various formats : currently to json, and to a Shapely polygon.
    """

    def __init__(self, runway_data):
        self.width = runway_data['width']
        self.end_1_id = runway_data['end_1_id']
        self.end_1_lat = runway_data['end_1_lat']
        self.end_1_lon = runway_data['end_1_lon']
        self.end_2_id = runway_data['end_2_id']
        self.end_2_lat = runway_data['end_2_lat']
        self.end_2_lon = runway_data['end_2_lon']

    def __repr__(self):
        return '<Runway: {} / {}>'.format(self.end_1_id, self.end_2_id)

    def __eq__(self, other):
        return other.name() == self.name() if isinstance(other, Runway) else NotImplemented

    def __hash__(self):
        return hash(self.name())

    def name(self):
        return tuple((self.end_1_id, self.end_2_id))

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

    def relevant_xptiles(self, include_surrounding_tiles=False):
        """Return the tiles where this runway is located (could be several ones)."""
        return [tile
                for end_tile in {XPlaneTile(self.end_1_lat, self.end_1_lon),
                                 XPlaneTile(self.end_2_lat, self.end_2_lon)}
                for tile in [end_tile] + (end_tile.surrounding_tiles() if include_surrounding_tiles else [])]

    def is_relevant_for(self, xptile, include_surrounding_tiles=False):
        """Is this runway part of the given tile ?"""
        return xptile in self.relevant_xptiles(include_surrounding_tiles)

    def _runway_center(self):
        geod = pyproj.Geod(ellps='WGS84')

        # First compute the azimuts and length between the two runway ends
        (azimut_1_2, azimut_2_1, length) = geod.inv(lons1=self.end_1_lon,
                                                    lats1=self.end_1_lat,
                                                    lons2=self.end_2_lon,
                                                    lats2=self.end_2_lat)

        # Then find the center of the runway, cache it and return it
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

        # Compute the two points near end_1
        (lon, lat, _) = geod.fwd(lons=self._runway_center().x,
                                 lats=self._runway_center().y,
                                 az=azimut_2_1,
                                 dist=(length + optimal_ground_dist) / 2)
        ((lon_1, lon_2), (lat_1, lat_2), _) = geod.fwd(lons=(lon, lon),
                                                       lats=(lat, lat),
                                                       az=(azimut_2_1 - 90.0,
                                                           azimut_2_1 + 90.0),
                                                       dist=(self.width / 2 + optimal_ground_dist / 4,
                                                             self.width / 2 + optimal_ground_dist / 4))
        coords.append((lon_1, lat_1))
        coords.append((lon_2, lat_2))

        # Then the two points near end_2
        ((lon_1, lon_2), (lat_1, lat_2), _) = geod.fwd(lons=(lon_1, lon_2),
                                                       lats=(lat_1, lat_2),
                                                       az=(azimut_1_2,
                                                           azimut_1_2),
                                                       dist=(length + optimal_ground_dist,
                                                             length + optimal_ground_dist))
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
        return filter(lambda gtile: prepared_polygon.intersects(gtile.polygon()),
                      [GTile(x, y, zl)
                       for x in range(x_min, x_max + 16, 16)
                       for y in range(y_min, y_max + 16, 16)])


class Airport:
    """A particular airport of an AirportCollection instance.

    Should be kept simple : its primary purpose is to hold some information about an airport,
    and to export itself to various formats : currently to json, and to a list of Shapely polygons.

    Runway information are stored in children instances of the Runway class.
    """

    def __init__(self, airport_data):
        self.type = airport_data['type']
        self.icao = airport_data['icao']
        self.name = airport_data['name']
        self.elevation = airport_data['elevation']
        self.runways = {rw.name(): rw for rw in [Runway(rw_data) for rw_data in airport_data['runways']]}

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

    def relevant_tiles(self, include_surrounding_tiles=False):
        """Return the tiles where this airport is located (could be several ones)."""
        return {tile
                for rw in self.runways.values()
                for tile in rw.relevant_xptiles(include_surrounding_tiles)}

    def to_json(self):
        return {
            'type': self.type,
            'icao': self.icao,
            'name': self.name,
            'elevation': self.elevation,
            'runways': [rw.to_json() for rw in self.runways.values()]
        }

    def gtiles(self, zl, screen_res, fov, fpa):
        return set(tile
                   for rw in self.runways.values()
                   for tile in rw.gtiles(zl, screen_res, fov, fpa))


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

    def __init__(self, airports=None):
        self.airports = {}
        if airports is None:
            pass
        elif isinstance(airports, Airport):
            self.airports[airports.icao] = airports
        elif isinstance(airports, AirportCollection):
            self.airports.update(airports)
        elif isinstance(airports, list):
            for a in airports:
                if isinstance(a, Airport):
                    self.airports[a.icao] = a
                elif isinstance(a, AirportCollection):
                    self.airports.update(a)
                else:
                    raise O4AirportDataSourceException("Incompatible element type")
        elif isinstance(airports, dict):
            for a in [Airport(v) for v in airports.values()]:
                self.airports[a.icao] = a
        else:
            raise O4AirportDataSourceException("Incompatible element type")
        self._cache_gtiles = {}

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
    # Airport Interface
    #

    def to_json(self):
        return {icao: arpt.to_json() for (icao, arpt) in self.airports.items()}

    def gtiles(self, zl, screen_res, fov, fpa):
        if (zl, screen_res, fov, fpa) in self._cache_gtiles:
            return self._cache_gtiles[(zl, screen_res, fov, fpa)]

        def sub_zl_margin():
            if zl == 19:
                return {}
            else:
                return set(tile
                           for step_1 in self.gtiles(zl + 1, screen_res, fov, fpa)
                           for step_2 in step_1.higher_zl_subtiles(target_zl=19)
                           for step_3 in step_2.surrounding_tiles(include_self=True)
                           for tile in step_3.lower_zl_tile(target_zl=zl).higher_zl_subtiles(target_zl=19))

        def airport_tiles():
            return set([tile
                        for airport in self.airports.values()
                        for subtile in airport.gtiles(zl, screen_res, fov, fpa)
                        for tile in subtile.higher_zl_subtiles(target_zl=19)])

        # First try to fill in the blanks, by minimizing the lower-zl tiles being more than 70% covered by higher-zl
        current_tiles = airport_tiles().union(sub_zl_margin())
        previous_tiles = set(current_tiles)
        for threshold_len in [0.70 * 2 ** (2 * (19 - i)) for i in range(18, 15, -1)]:
            previous_tiles = set(tile.lower_zl_tile() for tile in previous_tiles)
            for tile in previous_tiles:
                tmp_highest_zl = tile.higher_zl_subtiles(target_zl=19)
                if len(tmp_highest_zl.intersection(current_tiles)) >= threshold_len:
                    current_tiles.update(tmp_highest_zl)

        # Repeat the process until a full iteration went without changing anything (meaning: until we're done)
        previous_tiles = set()
        while current_tiles != previous_tiles:
            previous_tiles = current_tiles
            current_tiles = set()
            rejected_tiles = set()
            # Iterate through each tile, to see if something can be optimized
            for tile in sorted(previous_tiles):
                if tile in rejected_tiles:
                    # A sibling detected that this one is superseded by its lower_zl tile : ignore it
                    pass
                else:
                    siblings = tile.zl_siblings(include_self=True)
                    if len(siblings.intersection(previous_tiles)) == 4:
                        # They're already all in : replace them with their common lower zl tile
                        current_tiles.add(tile.lower_zl_tile())
                        rejected_tiles.update(siblings)
                    else:
                        # Nothing wrong with this one : add it as-is
                        current_tiles.add(tile)

        return sorted(current_tiles)

    def polygons(self, zl, screen_res, fov, fpa):
        """Return a Shapely polygon for the given combination of zl, screen_res, fov and fpa (see
        the docstring of zl_optimal_ground_dist() for a detailed explanation, with self-tests.

        Calls the polygons() method on each of its airports, and tries to merge the resulting polygons
        into as few new polygons as possible.
        """
        polys = shapely.ops.unary_union([gtile.polygon() for gtile in self.gtiles(zl, screen_res, fov, fpa)])
        if isinstance(polys, shapely.geometry.MultiPolygon):
            return list(polys)
        elif isinstance(polys, shapely.geometry.Polygon):
            return [polys]
        elif isinstance(polys, list):
            return polys
        else:
            return polys


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
    __RE_ARPT__ = re.compile('\s+'.join(['^(?P<airport_type>1|16|17)',
                                         '(?P<airport_elevation>\S+)',
                                         '(?P<airport_deprecated_1>\S+)',
                                         '(?P<airport_deprecated_2>\S+)',
                                         '(?P<airport_ICAO>\S+)',
                                         '(?P<airport_name>.*)']))

    __RE_IS_RWY__ = re.compile('^10[012]\s+')

    __RE_LAND_RWY__ = re.compile('\s+'.join(['^100',
                                             '(?P<runway_width>\S+)',
                                             '(?P<runway_surface>\S+)',
                                             '(?P<runway_shoulder_surface>\S+)',
                                             '(?P<runway_smoothness>\S+)',
                                             '(?P<runway_centerline_lights>\S+)',
                                             '(?P<runway_edge_lights>\S+)',
                                             '(?P<runway_distance_signs>\S+)',
                                             '(?P<runway_end_1_number>\S+)',
                                             '(?P<runway_end_1_latitude>\S+)',
                                             '(?P<runway_end_1_longitude>\S+)',
                                             '(?P<runway_end_1_displaced_threshold_length>\S+)',
                                             '(?P<runway_end_1_blastpad_length>\S+)',
                                             '(?P<runway_end_1_markings>\S+)',
                                             '(?P<runway_end_1_approach_lights>\S+)',
                                             '(?P<runway_end_1_touchdown_lights>\S+)',
                                             '(?P<runway_end_1_id_lights>\S+)',
                                             '(?P<runway_end_2_number>\S+)',
                                             '(?P<runway_end_2_latitude>\S+)',
                                             '(?P<runway_end_2_longitude>\S+)',
                                             '(?P<runway_end_2_displaced_threshold_length>\S+)',
                                             '(?P<runway_end_2_blastpad_length>\S+)',
                                             '(?P<runway_end_2_markings>\S+)',
                                             '(?P<runway_end_2_approach_lights>\S+)',
                                             '(?P<runway_end_2_touchdown_lights>\S+)',
                                             '(?P<runway_end_2_id_lights>\S+)']))

    __RE_WATER_RWY__ = re.compile('\s+'.join(['^101',
                                              '(?P<waterway_width>\S+)',
                                              '(?P<waterway_buoys>\S+)',
                                              '(?P<waterway_end_1_number>\S+)',
                                              '(?P<waterway_end_1_latitude>\S+)',
                                              '(?P<waterway_end_1_longitude>\S+)',
                                              '(?P<waterway_end_2_number>\S+)',
                                              '(?P<waterway_end_2_latitude>\S+)',
                                              '(?P<waterway_end_2_longitude>\S+)']))

    __RE_HELIPAD__ = re.compile('\s+'.join(['^102',
                                            '(?P<helipad_designator>\S+)',
                                            '(?P<helipad_center_latitude>\S+)',
                                            '(?P<helipad_center_longitude>\S+)',
                                            '(?P<helipad_orientation>\S+)',
                                            '(?P<helipad_length>\S+)',
                                            '(?P<helipad_width>\S+)',
                                            '(?P<helipad_surface>\S+)',
                                            '(?P<helipad_markings>\S+)',
                                            '(?P<helipad_shoulder_surface>\S+)',
                                            '(?P<helipad_smoothness>\S+)',
                                            '(?P<helipad_edge_lights>\S+)']))

    @staticmethod
    def _apt_dat_files_in(xp_dir):
        """Return the list of all the apt.dat files within the given X-Plane installation.
        The order is important : airports in the first files will be overwritten by those in the last ones (as in XP)"""
        apt_dat = os.path.join('Earth nav data', 'apt.dat')
        default_scenery = os.path.join(xp_dir, 'Resources', 'default scenery', 'default apt dat', apt_dat)
        global_airports = os.path.join(xp_dir, 'Custom Scenery', 'Global Airports', apt_dat)
        custom_airports = set(glob.glob(os.path.join(xp_dir, 'Custom Scenery', '*', apt_dat))) - {global_airports}
        return [default_scenery, global_airports] + sorted(custom_airports)

    def parse(self, *tiles):
        """Return one AirportCollection for each provided tile, will all the relevant airport data."""

        # Translation dicts
        airport_types = {'1': 'airport', '16': 'seaplane_base', '17': 'heliport'}

        # We'll only parse each file once, so we'll collect the airports in these AirportCollections along the way
        tile_airports = {tile: AirportCollection() for tile in tiles}

        for apt_dat_file in self._apt_dat_files_in(CFG.xplane_install_dir):
            with open(apt_dat_file, encoding='latin9') as apt_dat:
                current_airport = None  # We'll only add an airport to 'parsed_airport' if it has a relevant runway
                for src_line in apt_dat:
                    m = XPlaneAptDatParser.__RE_ARPT__.match(src_line)
                    if m:
                        current_airport = Airport({
                            'type': airport_types[m.group('airport_type')],
                            'icao': m.group('airport_ICAO'),
                            'name': m.group('airport_name'),
                            'elevation': m.group('airport_elevation'),
                            'runways': []
                        })

                    elif XPlaneAptDatParser.__RE_IS_RWY__.match(src_line):
                        # TODO: XPlaneAptDatParser: also parse seaplane bases et heliports
                        m = XPlaneAptDatParser.__RE_LAND_RWY__.match(src_line)
                        if m:
                            runway = Runway({
                                'end_1_id': m.group('runway_end_1_number'),
                                'end_1_lat': numpy.float(m.group('runway_end_1_latitude')),
                                'end_1_lon': numpy.float(m.group('runway_end_1_longitude')),
                                'end_2_id': m.group('runway_end_2_number'),
                                'end_2_lat': numpy.float(m.group('runway_end_2_latitude')),
                                'end_2_lon': numpy.float(m.group('runway_end_2_longitude')),
                                'width': numpy.float(m.group('runway_width'))})

                            # Check if this runway is relevant to each tile.
                            # If so :
                            # - ensure the airport is in the corresponding AirportCollection
                            # - add the runway to the airport
                            for rw_tile in runway.relevant_xptiles(include_surrounding_tiles=False):
                                if rw_tile in tile_airports:
                                    # If old airport information was already there, it will be overwritten here :
                                    # this is intentional (same behavior as X-Plane).
                                    tile_airports[rw_tile][current_airport.icao] = current_airport
                                    tile_airports[rw_tile][current_airport.icao][runway.name()] = runway
        return tile_airports


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

    __PARSER_CLASSES__ = [XPlaneAptDatParser]  # [OSMAirportsParser, XPlaneAptDatParser]

    def __init__(self):
        self._index_by_tile = {}

    def airports_in(self, tiles, include_surrounding_tiles=False):
        """Return an AirportCollection of all the airports in the given tile(s)."""

        # Optionally add the surrounding tiles to the search range
        search_range = set(tiles)
        if include_surrounding_tiles:
            for t in tiles:
                search_range.update(t.surrounding_tiles())

        # For now, skip the tiles that already are in the in-memory index
        missing_tiles = []
        for tile in filter(lambda x: x not in self._index_by_tile, search_range):
            # Try looking at the filesystem cache : this will load it in the in-memory index
            try:
                self._read_cached_tile(tile)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                # If we can't find or decode the cached data for whatever reason, then just add it to the rebuild list
                missing_tiles.append(tile)

        # (Re-)build the missing cache files, if any (this will also load them in the in-memory index)
        if missing_tiles:
            self._rebuild_tile_cache(*missing_tiles)

        # Now we should have all the tiles in memory, return their airports
        return AirportCollection([self._index_by_tile[tile] for tile in search_range])

    def _read_cached_tile(self, tile):
        """Read the given tile airports from the filesystem cache"""
        with open(FNAMES.cached_arpt_data(lat=tile.lat, lon=tile.lon)) as fd:
            # First read the airports from the cache file
            airports = AirportCollection([Airport(a) for a in json.load(fd).values()])
            # Then load them in the in-memory index and return them
            return self._index_by_tile.setdefault(tile, airports)

    def _rebuild_tile_cache(self, *tiles):
        """(Re-)Build the filesystem cache for the given tile(s).
        And while we're at it, also rebuilt the surrounding tiles cache, we'll probably need them soon."""

        # Invoke each parser on the list of tiles, and update the in-memory index with the results
        for parser in [parser_class() for parser_class in AirportDataSource.__PARSER_CLASSES__]:
            self._index_by_tile.update({tile: airport_collection
                                        for (tile, airport_collection) in parser.parse(*tiles).items()})

        # Finally, cache the parsed data to the filesystem
        for tile in tiles:
            tile_cache_file = FNAMES.cached_arpt_data(lat=tile.lat, lon=tile.lon)
            os.makedirs(os.path.dirname(tile_cache_file), exist_ok=True)
            with open(tile_cache_file, 'w') as f:
                json.dump(self._index_by_tile[tile].to_json(), f, sort_keys=True, indent=True)

# eof
