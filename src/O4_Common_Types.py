import enum
import re

import numpy


class IcaoCode:
    """Simple utility class to represent an ICAO code.
    It is capable of checking whether the ICAO code is a valid one or not.
    Useful to distinguish between major airports with valid ICAO code, versus local aerodromes, or even fictional ones.
    The list of ICAO region prefixes comes from Wikipedia as of 2019-05-27 (good enough for our non-operational use)
    """
    __TWO_CHARS_ICAO_REGIONS__ = {
        # A - Western South Pacific
        "AG", "AN", "AY",
        # B - Greenland, Iceland, and Kosovo (European Alternate)
        "BG", "BI", "BK",
        # D – Eastern parts of West Africa and Maghreb
        "DA", "DB", "DF", "DG", "DI", "DN", "DR", "DT", "DX",
        # E – Northern Europe
        "EB", "ED", "EE", "EF", "EG", "EH", "EI", "EK", "EL", "EN", "EP", "ES", "ET", "EV", "EY",
        # F – Most of Central Africa and Southern Africa, and the Indian Ocean
        "FA", "FB", "FC", "FD", "FE", "FG", "FH", "FI", "FJ", "FK", "FL", "FM", "FN", "FO", "FP", "FQ", "FS", "FT",
        "FV", "FW", "FX", "FY", "FZ",
        # G – Western parts of West Africa and Maghreb
        "GA", "GB", "GC", "GE", "GF", "GG", "GL", "GM", "GO", "GQ", "GS", "GU", "GV",
        # H – East Africa and Northeast Africa
        "HA", "HB", "HC", "HD", "HE", "HH", "HK", "HL", "HR", "HS", "HT", "HU",
        # L – Southern Europe, Israel and Turkey
        "LA", "LB", "LC", "LD", "LE", "LF", "LG", "LH", "LI", "LJ", "LK", "LL", "LM", "LN", "LO", "LP", "LQ", "LR",
        "LS", "LT", "LU", "LV", "LW", "LX", "LY", "LZ",
        # M – Central America, Mexico and northern/western parts of the Caribbean
        "MB", "MD", "MG", "MH", "MK", "MM", "MN", "MP", "MR", "MS", "MT", "MU", "MW", "MY", "MZ",
        # N – Most of the South Pacific
        "NC", "NF", "NG", "NI", "NL", "NS", "NT", "NV", "NW", "NZ",
        # O – Pakistan, Afghanistan and most of Middle East
        # (excluding Cyprus, Israel, Turkey, and the South Caucasus)
        "OA", "OB", "OE", "OI", "OJ", "OK", "OL", "OM", "OO", "OP", "OR", "OS", "OT", "OY",
        # P – (Former)American North Pacific and Kiribati
        "PA", "PB", "PC", "PF", "PG", "PH", "PJ", "PK", "PL", "PM", "PO", "PP", "PT", "PW",
        # R – Taiwan/South Korea/Philippines and Japan
        "RC", "RJ", "RK", "RO", "RP",
        # S – South America
        "SA", "SB", "SC", "SD", "SE", "SF", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SP", "SS", "SU",
        "SV", "SW", "SY",
        # T – Eastern and southern parts of the Caribbean
        "TA", "TB", "TD", "TF", "TG", "TI", "TJ", "TK", "TL", "TN", "TQ", "TR", "TT", "TU", "TV", "TX",
        # U – Russia and post-Soviet states, excluding the Baltic states and Moldova
        "UA", "UB", "UC", "UD", "UG", "UK", "UM", "UT",
        # V – South Asia (except Afghanistan and Pakistan),
        # mainland Southeast Asia, Hong Kong and Macau
        "VA", "VC", "VD", "VE", "VG", "VH", "VI", "VL", "VM", "VN", "VO", "VQ", "VR", "VT", "VV", "VY",
        # W – Maritime Southeast Asia (except the Philippines)
        "WA", "WB", "WI", "WM", "WP", "WQ", "WR", "WS",
        # Z –(Former)Socialist East Asia
        "ZK", "ZM"
    }

    __ONE_CHAR_ICAO_REGIONS__ = {
        # C - Canada
        "C",
        # K – Contiguous United States
        "K",
        # Australia (including Norfolk Island, Christmas Island and Cocos (Keeling) Islands)
        "Y"
    }

    __RE_ICAO_REGION__ = re.compile('(' + '|'.join([
        # Russia (except UA, UB, UC, UD, UG, UK, UM and UT)
        "U[^ABCDGKMT][A-Z]{2}",
        # Mainland China (except ZK and ZM)
        "Z[^KM][A-Z]{2}"
    ]) + ')')

    def __init__(self, icao_str):
        if isinstance(icao_str, IcaoCode):
            self._icao = icao_str._icao
        elif isinstance(icao_str, str):
            self._icao = icao_str.upper()
        else:
            raise ValueError("The ICAO code must be either an str, or another instance of IcaoCode")

    def __repr__(self):
        if self.is_valid:
            return '<ICAO: {}>'.format(self._icao)
        else:
            return '<ICAO: {} (Invalid)>'.format(self._icao)

    def __str__(self):
        if not isinstance(self._icao, str):
            return NotImplemented
        return self._icao

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, IcaoCode):
            return NotImplemented
        return self._icao == other._icao

    @property
    def icao(self):
        return self._icao

    @property
    def is_valid(self):
        # Standard robustness
        if not isinstance(self._icao, str):
            return False
        if len(self._icao) != 4:
            return False

        # Test order is important here : first two-chars, then one-char, then regex
        if self._icao[0:2] in self.__TWO_CHARS_ICAO_REGIONS__:
            return True
        if self._icao[0] in self.__ONE_CHAR_ICAO_REGIONS__:
            return True
        if self.__RE_ICAO_REGION__.match(self._icao):
            return True

        # Doesn't match anything => not a valid ICAO code
        return False


class ZoomLevelsMeta(type):
    """Metaclass for ZoomLevels class.
    Used to dynamically build a few dictionaries of color gradients for each Zoom Level.
    This is run only once at load time, when the ZoomLevels class itself is created.
    Afterward at run time, the ZoomLevels utility functions will boil down to simple (and fast) dictionary accesses"""
    # Constants
    __ZL_MIN__ = 12
    __ZL_LOW__ = 15
    __ZL_HIGH__ = 18
    __ZL_MAX__ = 19
    __ZL_OVERKILL__ = 21

    # Common zoom level ranges
    ALL = list(range(__ZL_MIN__, __ZL_MAX__ + 1))
    OSM_LEVELS = [11, 12, 13]
    CUSTOM_LEVELS = list(range(__ZL_LOW__, __ZL_MAX__ + 1))

    __MAX_OPACITY__ = 0xFF * 0.70
    __ZL_DIFF_MAX__ = __ZL_OVERKILL__ - __ZL_MIN__

    def __new__(mcs, *args, **kwargs):
        new_class = super(ZoomLevelsMeta, mcs).__new__(mcs, *args, **kwargs)

        rgb_colors_dict = {zl: color
                           for (zl, color) in mcs._heat_map(cold_zls=range(mcs.__ZL_MIN__, mcs.__ZL_LOW__),
                                                            temperate_zls=range(mcs.__ZL_LOW__, mcs.__ZL_HIGH__),
                                                            warm_zls=range(mcs.__ZL_HIGH__, mcs.__ZL_MAX__ + 1),
                                                            blazing_zls=range(mcs.__ZL_MAX__ + 1,
                                                                              mcs.__ZL_OVERKILL__ + 1))}

        rgba_colors_dict = {zl: (r, g, b, int(mcs.__MAX_OPACITY__ * (zl - mcs.__ZL_MIN__) / mcs.__ZL_DIFF_MAX__))
                            for zl in range(mcs.__ZL_MIN__, mcs.__ZL_OVERKILL__ + 1)
                            for (r, g, b) in [rgb_colors_dict[zl]]}

        rgba_border_colors_dict = {zl: (0x00, 0x00, 0x00,
                                        int(mcs.__MAX_OPACITY__ - mcs.__MAX_OPACITY__ *
                                            (zl - mcs.__ZL_MIN__) / mcs.__ZL_DIFF_MAX__))
                                   for zl in range(mcs.__ZL_MIN__, mcs.__ZL_OVERKILL__ + 1)}

        tkinter_fg_colors_dict = {zl: ('#000000' if mcs.__ZL_MIN__ <= zl <= mcs.__ZL_MAX__ else '#FFFFFF')
                                  for zl in range(mcs.__ZL_MIN__, mcs.__ZL_OVERKILL__ + 1)}

        tkinter_colors_dict = {zl: '#{0[0]:02X}{0[1]:02X}{0[2]:02X}'.format(rgb_colors_dict[zl])
                               for zl in range(mcs.__ZL_MIN__, mcs.__ZL_OVERKILL__ + 1)}

        setattr(new_class, '_rgb_colors_dict', rgb_colors_dict)
        setattr(new_class, '_rgba_colors_dict', rgba_colors_dict)
        setattr(new_class, '_rgba_border_colors_dict', rgba_border_colors_dict)
        setattr(new_class, '_tkinter_fg_colors_dict', tkinter_fg_colors_dict)
        setattr(new_class, '_tkinter_colors_dict', tkinter_colors_dict)

        return new_class

    @staticmethod
    def _heat_map(cold_zls, temperate_zls, warm_zls, blazing_zls):
        """Return a gradient of colors for the provided groups of zoom levels"""
        cold_range = ((0x00, 0xFF, 0xFF),  # cyan
                      (0x66, 0xCD, 0xAA))  # medium aquamarine
        temperate_range = ((0x66, 0xCD, 0xAA),  # medium aquamarine
                           (0x00, 0x80, 0x00))  # green
        warm_range = ((0xFF, 0xA5, 0x00),  # orange
                      (0xFF, 0x00, 0x00))  # red
        blazing_range = ((0x80, 0x00, 0x00),  # dark red
                         (0x00, 0x00, 0x00))  # black

        cold = zip(*(numpy.linspace(x[0], x[1], len(cold_zls), dtype=int)
                     for x in zip(*cold_range)))

        temperate = zip(*(numpy.linspace(x[0], x[1], len(temperate_zls), dtype=int)
                          for x in zip(*temperate_range)))

        warm = zip(*(numpy.linspace(x[0], x[1], len(warm_zls), dtype=int)
                   for x in zip(*warm_range)))

        blazing = zip(*(numpy.linspace(x[0], x[1], len(blazing_zls), dtype=int)
                      for x in zip(*blazing_range)))

        hm = list(zip(list(cold_zls) + list(temperate_zls) + list(warm_zls) + list(blazing_zls),
                      list(cold) + list(temperate) + list(warm) + list(blazing)))
        return hm


class ZoomLevels(metaclass=ZoomLevelsMeta):
    """Doesn't represent a ZoomLevel, just regroups a set of utility functions to associate colors to individual ZL"""
    # Rewrite those, to help with IDE inspection
    __ZL_MIN__ = ZoomLevelsMeta.__ZL_MIN__
    __ZL_MAX__ = ZoomLevelsMeta.__ZL_MAX__

    @classmethod
    def normalized(cls, zl, min_zl=None, max_zl=None):
        """Ensure the provided ZL is between __ZL_MIN__ and __ZL_MAX."""
        return max(min(int(zl) + 1,
                       max_zl or cls.__ZL_MAX__),
                   min_zl or cls.__ZL_MIN__)

    @classmethod
    def rgb_color_of(cls, zl):
        return cls._rgb_colors_dict[zl]

    @classmethod
    def rgba_color_of(cls, zl):
        return cls._rgba_colors_dict[zl]

    @classmethod
    def rgba_border_color_of(cls, zl):
        return cls._rgba_border_colors_dict[zl]

    @classmethod
    def tkinter_fg_color_of(cls, zl):
        return cls._tkinter_fg_colors_dict[zl]

    @classmethod
    def tkinter_color_of(cls, zl):
        return cls._tkinter_colors_dict[zl]


class CoverZLConfig:
    """Used to parse and represent the 'cover_zl' configuration value, which can be either an int (simple case), or a
    dictionary to customize the 'cover_zl' per kind of airport (ICAO vs non-ICAO), or even per airport (ICAO code)
    """
    def __init__(self, cover_zl_cfg):
        _cover_zl_cfg = int(cover_zl_cfg) if isinstance(cover_zl_cfg, str) else cover_zl_cfg
        if isinstance(_cover_zl_cfg, int):
            self.default = _cover_zl_cfg
            self.icao = _cover_zl_cfg
            self.non_icao = _cover_zl_cfg
            self.by_icao = dict()
            self.max = _cover_zl_cfg
        elif isinstance(_cover_zl_cfg, dict):
            if 'default' not in _cover_zl_cfg:
                raise Exception('CoverZL must be either an int, or a dict which MUST contain a "default" item')
            self.default = _cover_zl_cfg.pop('default')
            self.icao = _cover_zl_cfg.pop('icao') if 'icao' in _cover_zl_cfg else self.default
            self.non_icao = _cover_zl_cfg.pop('non_icao') if 'non_icao' in _cover_zl_cfg else self.default
            self.by_icao = {IcaoCode(k): v for (k, v) in _cover_zl_cfg.items()}
            self.max = max(self.default, self.icao, self.non_icao, *list(self.by_icao.values()))
        else:
            raise Exception('CoverZL must be either an int, or a dict which MUST contain a "default" item')

    def max_cover_zl_for(self, airport_icao: IcaoCode):
        """
        >>> airports = [IcaoCode(a) for a in ['KSBP', 'KSMX', 'L52', 'L88']]

        >>> cfg = CoverZLConfig(15)
        >>> cfg.max
        15
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [15, 15, 15, 15]

        >>> cfg = CoverZLConfig({'default': 15})
        >>> cfg.max
        15
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [15, 15, 15, 15]

        >>> cfg = CoverZLConfig({'default': 15, 'non_icao': 16})
        >>> cfg.max
        16
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [15, 15, 16, 16]

        >>> cfg = CoverZLConfig({'default': 15, 'icao': 17})
        >>> cfg.max
        17
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [17, 17, 15, 15]

        >>> cfg = CoverZLConfig({'default': 15, 'non_icao':16, 'icao': 17})
        >>> cfg.max
        17
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [17, 17, 16, 16]

        >>> cfg = CoverZLConfig({'default': 15, 'non_icao': 16, 'L52': 19})
        >>> cfg.max
        19
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [15, 15, 19, 16]

        >>> cfg = CoverZLConfig({'default': 15, 'icao': 17, 'KSBP': 19})
        >>> cfg.max
        19
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [19, 17, 15, 15]

        >>> cfg = CoverZLConfig({'default': 15, 'non_icao':16, 'icao': 17, 'L52': 19, 'KSBP': 19})
        >>> cfg.max
        19
        >>> [cfg.max_cover_zl_for(airport) for airport in airports]
        [19, 17, 19, 16]
        """
        if airport_icao in self.by_icao:
            return self.by_icao[airport_icao]

        if airport_icao.is_valid:
            return self.icao

        return self.non_icao


class ScreenRes(enum.Enum):
    """An enum for the 'cover_screen_res' configuration value"""
    res_720p = (1280, 720)
    SD = res_720p
    res_1080p = (1920, 1080)
    HD = res_1080p
    res_1440p = (2560, 1440)
    QHD = res_1440p
    res_2160p = (3840, 2160)
    res_4K = res_2160p
    res_4320p = (7680, 4320)
    res_8K = res_4320p
    OculusRift = (1080, 1200)  # Per eye
    HtcVive = (1080, 1200)  # Per eye
    HtcVivePro = (1440, 1600)  # Per eye

    __FROM_STR__ = {'SD_720p': res_720p,
                    'HD_1080p': res_1080p,
                    'QHD_1440p': res_1440p,
                    '4K_2160p': res_2160p,
                    'OculusRift': OculusRift,
                    'HtcVive': HtcVive,
                    'HtcVivePro': HtcVivePro}

    @classmethod
    def from_config_value(cls, config_value):
        """Parse the config value, and return the horizontal part of the corresponding screen resolution"""
        if isinstance(config_value, ScreenRes):
            return config_value[0]
        if isinstance(config_value, int):
            return config_value
        elif isinstance(config_value, str) and config_value in cls.__FROM_STR__:
            return cls.__FROM_STR__[config_value][0]
        else:
            raise ValueError("Unsupported ScreenRes value. Accepted values are {}, "
                             "or an integer (horizontal resolution)".format(sorted(cls.__FROM_STR__.keys())))
