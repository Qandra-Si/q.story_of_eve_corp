import typing
from math import sqrt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import csv

import eve_sde_tools


# Смотрим рекомендуемые настройки кодирования здесь https://support.google.com/youtube/answer/1722171?hl=ru
# выбираем частоту кадров, разрешение и соотношение сторон, останавливаемся на Ultra HD 4K.
# Внимание! крайне не рекомендуется менять следующие параметры, задавая их отличными от одного из перечисленных
# по ссылке вариантов, во избежание перекодирования изображений сгенерированных этой программой. Изображения содержат
# текст, которые после переконвертации может стать плохочитаемым.
RENDER_WIDTH: int = 3840
RENDER_HEIGHT: int = 2160
RENDER_FRAME_RATE: int = 24  # 24
SOLAR_SYSTEM_FATNESS: float = 2.0
LUMINOSITY_MIN_BOUND: int = 50  # 50 хорошо в тёмное время суток на тёмном экране, 100 днём очень ярко для killmails
LUMINOSITY_MAX_BOUND: int = 255
NUMBER_OF_EVENTS: int = 50
NUMBER_OF_KILLMAILS_IN_LIST: int = 30  # шрифт используется такой же, регион для killmails занимает меньше места
KILLMAIL_MAP_MIN_ALPHA: float = 220  # 255 максимальный уровень непрозрачности
KILLMAIL_MAP_MAX_ALPHA: float = 50   # 0 максимальный уровень прозрачности
KILLMAIL_MIN_FATNESS: float = SOLAR_SYSTEM_FATNESS * 4  # маркер гибели корабля больше солнечной системы, далее по массе
INDUSTRY_MIN_FATNESS: float = SOLAR_SYSTEM_FATNESS * 5  # маркер производства больше солнечной системы, далее по ранам
INDUSTRY_MAP_MIN_ALPHA: float = 220  # 255 максимальный уровень непрозрачности
INDUSTRY_MAP_MAX_ALPHA: float = 128  # 0 максимальный уровень прозрачности
MARKET_MAP_MIN_ALPHA: float = 220    # 255 максимальный уровень непрозрачности
MARKET_MAP_MAX_ALPHA: float = 128    # 0 максимальный уровень прозрачности
# интервалы времени (д.б. согласованы с RENDER_FRAME_RATE)
DURATION_DATE_SEC: int = 1  # одна дата рисуется 2 секунды
DURATION_DATE: int = RENDER_FRAME_RATE * DURATION_DATE_SEC  # одна дата рисуется 2*24 фрейма, т.е. 2 секунды
# цвета, выбираем тут https://www.computerhope.com/htmcolor.htm
EVENTS_SETUP: ((int, int, int), int) = [
    # color              duration sec
    ((0xff, 0xe5, 0xb4), 8),  # peach (персиковый) warning "Hello, Qandra Si", живёт на экране 8 секунд
    ((0xb6, 0xb6, 0xb4), 4),  # gray cloud (светло серый) notice "Qandra Si has come", живёт на экране 4 секунды
    ((0x79, 0x79, 0x79), 3),  # platinum gray (сероватый) notice "Qandra Si gone", живёт на экране 3 секунды
    ((0xc9, 0xc0, 0xbb), 5),  # pale silver (сёро жёлтая) надпись рекорд производственных работ, живёт 5 секунд
    ((0x73, 0x7c, 0xa1), 5),  # slate blue grey (сёро голубая) надпись рекорд рыночных операций, живёт 5 секунд
]
KILLMAILS_SETUP: (int, int, int) = [
    # color              duration sec
    ((0xdc, 0x38, 0x1f), DURATION_DATE_SEC),      # (в списке событий killmail не упоминается), живёт на экране одни сутки
    ((0xdc, 0x38, 0x1f), DURATION_DATE_SEC * 2),  # grapefruit (красный) warning "Zorky Graf Tumidus lost Rhea", живёт на экране 2 суток
    ((0x12, 0xad, 0x2b), DURATION_DATE_SEC),      # (в списке событий killmail не упоминается), живёт на экране одни сутки
    ((0x12, 0xad, 0x2b), DURATION_DATE_SEC * 2),  # parrot green (зелёный) warning "Astrahus destroyed by 240 pilots", живёт на экране 2 суток
]
INDUSTRY_SETUP: (int, int, int) = (0xff, 0xdf, 0x00)  # golden yellow (жёлтый) производственные работы
MARKET_SETUP: (int, int, int) = (0x5c, 0xb3, 0xff)    # crystal blue (синий) операции на рынке

# формат csv файла events-utf8.txt
FILE_EVENTS_NAME: str = "events-utf8.txt"
FILE_EVENTS_COL_DATE: int = 0
FILE_EVENTS_COL_LEVEL: int = 1
FILE_EVENTS_COL_TXT: int = 2
# формат csv файла killmails-utf8.txt
FILE_KILLMAILS_NAME: str = "killmails-utf8.txt"
FILE_KILLMAILS_COL_DATE: int = 0
FILE_KILLMAILS_COL_VICTIM: int = 1
FILE_KILLMAILS_COL_SHIPTYPE: int = 2
FILE_KILLMAILS_COL_MASS: int = 3
FILE_KILLMAILS_COL_TXT: int = 4
FILE_KILLMAILS_COL_SYSTEM: int = 5
# формат csv файла industry_jobs-utf8.txt
FILE_INDUSTRY_NAME: str = "industry_jobs-utf8.txt"
FILE_INDUSTRY_COL_DATE: int = 0
FILE_INDUSTRY_COL_JOBS: int = 1
FILE_INDUSTRY_COL_SYSTEM: int = 2
# формат csv файла market-utf8.txt
FILE_MARKET_NAME: str = "market-utf8.txt"
FILE_MARKET_COL_DATE: int = 0
FILE_MARKET_COL_SYSTEM: int = 1
FILE_MARKET_COL_ISK: int = 2


class RenderScale:
    def __init__(self):
        # данные, полученные из позиций солнечных систем
        self.min_x: float = 0.0
        self.max_x: float = 0.0
        self.min_z: float = 0.0
        self.max_z: float = 0.0
        self.min_luminosity: float = 0.0
        self.max_luminosity: float = 0.0
        self.universe_center_x: float = 0.0
        self.universe_center_z: float = 0.0
        self.universe_width: float = 0.0
        self.universe_height: float = 0.0
        # настройки рендеринга изображения
        self.render_center_width: float = RENDER_WIDTH / 2.0
        self.render_half_height: float = RENDER_HEIGHT / 2.0  # выполняет роль стороны квадрата, куда будут вписаны SS
        self.scale_x: float = 0.0
        self.scale_z: float = 0.0
        self.scale_luminosity: float = 0.0
        # размер шрифтов для рисования ндписей на картинке
        self.fontsize = 1
        self.left_bound_of_events: int = 0

    def calc(self, sde_positions):
        self.min_x = None
        for p in sde_positions.values():
            if self.min_x is None:
                self.min_x = p[0]
                self.max_x = p[0]
                self.min_z = p[2]
                self.max_z = p[2]
                self.min_luminosity = p[3]
                self.max_luminosity = p[3]
            else:
                if self.min_x > p[0]:
                    self.min_x = p[0]
                if self.max_x < p[0]:
                    self.max_x = p[0]
                if self.min_z > p[2]:
                    self.min_z = p[2]
                if self.max_z < p[2]:
                    self.max_z = p[2]
                if self.min_luminosity > p[3]:
                    self.min_luminosity = p[3]
                if self.max_luminosity < p[3]:
                    self.max_luminosity = p[3]
        # получаем сводную информацию
        self.universe_center_x = self.max_x - (self.max_x - self.min_x) / 2.0
        self.universe_center_z = self.max_z - (self.max_z - self.min_z) / 2.0
        self.universe_width = self.max_x - self.min_x
        self.universe_height = self.max_z - self.min_z
        # поскольку прямоугольник изображения горизонтально-ориентированный, то по высоте он короче...
        self.scale_z = RENDER_HEIGHT / self.universe_height
        self.scale_x = RENDER_HEIGHT / self.universe_width
        # рассчитываем позицию региона, где будут появляться события
        self.left_bound_of_events: int = int(self.render_center_width + (self.max_x-self.universe_center_x)*self.scale_x) + 20
        # расчёт светимости, берём мощность от яркости, как корень квадратный
        self.min_luminosity = sqrt(self.min_luminosity)
        self.max_luminosity = sqrt(self.max_luminosity)
        self.scale_luminosity: float = (LUMINOSITY_MAX_BOUND - LUMINOSITY_MIN_BOUND) / (self.max_luminosity - self.min_luminosity)

    def choose_font_size(self):
        self.fontsize: int = 10  # начальный размер шрифта
        font = ImageFont.truetype("arial.ttf", self.fontsize)
        # итерируемся по размерам шрифтов так, чтобы в высоту изображения влезло N строк
        while font.getsize("Qandra Si")[1] < (RENDER_HEIGHT / NUMBER_OF_EVENTS):
            self.fontsize += 1
            font = ImageFont.truetype("arial.ttf", self.fontsize)
        # опционально уменьшаем размер шрифта, чтобы была уверенность, что символы не будут наползать друг на друга
        self.fontsize -= 1
        del font


class RenderFadeInEvent:
    def __init__(self, txt: str, level: int):
        self.txt: str = txt
        self.__color: (int, int, int) = EVENTS_SETUP[level][0]
        self.opacity: float = 1.0
        lifetime_frames: int = EVENTS_SETUP[level][1] * RENDER_FRAME_RATE
        self.transparency_frame: float = 1.0 / lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.opacity -= self.transparency_frame
        if self.opacity < 0.0:
            self.opacity = 0.0

    @property
    def color(self) -> (int, int, int):
        return int(self.__color[0] * self.opacity), int(self.__color[1] * self.opacity), int(self.__color[2] * self.opacity)

    @property
    def disappeared(self) -> bool:
        return self.opacity < 0.08


class RenderFadeInKillmail:
    __do_not_show_in_list: typing.Set[int] = {
        583, 670,  # Capsule
        588, 596, 601, 606,  # Corvette
        648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 1944, 19744, 32880,  # Industrial (cyno?)
        672, 11129, 11132, 11134,  # Shuttle,
        33474, 33520,  # Mobile Depot
        33591,  # Mobile Micro Jump Unit
        33475,  # Mobile Tractor Unit
        57319,  # Mobile Cynosural Beacon
    }

    def __init__(
            self,
            victim: bool,
            txt: str,
            ship_type: int,
            ship_mass: float,
            x: typing.Optional[float],
            z: typing.Optional[float]):
        if victim:
            if ship_type in self.__do_not_show_in_list:
                self.__level: int = 0
            else:
                self.__level: int = 1
        else:
            if ship_type in self.__do_not_show_in_list:
                self.__level: int = 2
            else:
                self.__level: int = 3
        self.__color: typing.Optional[(int, int, int)] = KILLMAILS_SETUP[self.__level][0]
        self.txt: str = txt
        self.mass: float = ship_mass
        self.x: typing.Optional[float] = x
        self.z: typing.Optional[float] = z
        self.opacity: float = 1.0
        self.frame_num: int = 1
        self.lifetime_frames: int = KILLMAILS_SETUP[self.__level][1] * RENDER_FRAME_RATE
        self.transparency_frame: float = 1.0 / self.lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.frame_num += 1
        self.lifetime_frames -= 1
        self.opacity -= self.transparency_frame
        if self.opacity < 0.0:
            self.opacity = 0.0

    @property
    def show_in_list(self) -> bool:
        return self.__level == 1 or self.__level == 3

    @property
    def show_on_map(self) -> bool:
        return self.x is not None

    @property
    def disappeared(self) -> bool:
        return self.lifetime_frames == 0

    @property
    def list_color(self) -> (int, int, int):
        return int(self.__color[0] * self.opacity), int(self.__color[1] * self.opacity), int(self.__color[2] * self.opacity)

    @property
    def map_color(self) -> (int, int, int):
        return self.__color

    @property
    def map_alpha(self) -> int:
        return int(KILLMAIL_MAP_MIN_ALPHA + (1.0-self.opacity) * (KILLMAIL_MAP_MAX_ALPHA - KILLMAIL_MAP_MIN_ALPHA))

    @property
    def map_radius(self) -> float:
        # в первые треть секунды радиус взрыва растёт, пока на достигнет эквивалента массы
        boom_radius: float = self.mass / 50000000  # Rhea 960'000'000, Capsule 32'000, Venture 1'200'000
        if boom_radius < KILLMAIL_MIN_FATNESS:
            boom_radius = KILLMAIL_MIN_FATNESS
        half_sec_frames: int = int((RENDER_FRAME_RATE + 1) / 3)
        if self.frame_num < half_sec_frames:
            boom_radius *= self.frame_num / half_sec_frames
        return boom_radius


class RenderFadeInIndustry:
    def __init__(
            self,
            runs: int,
            x: typing.Optional[float],
            z: typing.Optional[float]):
        self.runs: int = runs
        self.x: typing.Optional[float] = x
        self.z: typing.Optional[float] = z
        self.frame_num: int = 1
        self.transparency_frame: float = 2.0 / (RENDER_FRAME_RATE * DURATION_DATE_SEC)  # мера прозрачности, добавляемая каждый фрейм
        self.opacity: float = 0.0

    def pass_frame(self):
        self.frame_num += 1
        if self.frame_num < (RENDER_FRAME_RATE * DURATION_DATE_SEC + 1) / 2:
            self.opacity += self.transparency_frame
            if self.opacity > 1.0:
                self.opacity = 1.0
        else:
            self.opacity -= self.transparency_frame
            if self.opacity < 0.0:
                self.opacity = 0.0

    @property
    def disappeared(self) -> bool:
        return self.frame_num > (RENDER_FRAME_RATE * DURATION_DATE_SEC)

    @property
    def map_color(self) -> (int, int, int):
        return INDUSTRY_SETUP

    @property
    def map_alpha(self) -> int:
        return int(INDUSTRY_MAP_MIN_ALPHA + (1.0-self.opacity) * (INDUSTRY_MAP_MAX_ALPHA - INDUSTRY_MAP_MIN_ALPHA))

    @property
    def map_radius(self) -> float:
        industry_radius: float = 13 * self.runs / 1000  # 2022-02-02 : 2581 работ
        half_date_frames: int = int((RENDER_FRAME_RATE * DURATION_DATE_SEC + 1) / 2)
        if self.frame_num < half_date_frames:
            industry_radius *= self.frame_num / half_date_frames
        else:
            industry_radius *= (RENDER_FRAME_RATE * DURATION_DATE_SEC - self.frame_num) / half_date_frames
        return INDUSTRY_MIN_FATNESS + industry_radius


class RenderFadeInMarket:
    def __init__(
            self,
            isk: float,
            x: typing.Optional[float],
            z: typing.Optional[float]):
        self.isk: int = int(isk)
        self.x: typing.Optional[float] = x
        self.z: typing.Optional[float] = z
        self.frame_num: int = 1
        self.transparency_frame: float = 2.0 / (RENDER_FRAME_RATE * DURATION_DATE_SEC)  # мера прозрачности, добавляемая каждый фрейм
        self.opacity: float = 0.0

    def pass_frame(self):
        self.frame_num += 1
        if self.frame_num < (RENDER_FRAME_RATE * DURATION_DATE_SEC + 1) / 2:
            self.opacity += self.transparency_frame
            if self.opacity > 1.0:
                self.opacity = 1.0
        else:
            self.opacity -= self.transparency_frame
            if self.opacity < 0.0:
                self.opacity = 0.0

    @property
    def disappeared(self) -> bool:
        return self.frame_num > (RENDER_FRAME_RATE * DURATION_DATE_SEC)

    @property
    def map_color(self) -> (int, int, int):
        return MARKET_SETUP

    @property
    def map_alpha(self) -> int:
        return int(MARKET_MAP_MIN_ALPHA + (1.0-self.opacity) * (MARKET_MAP_MAX_ALPHA - MARKET_MAP_MIN_ALPHA))

    @property
    def map_radius(self) -> float:
        market_radius: float = 13 * self.isk / 20000000000  # 2021-12-09 : 74'161'872'333 isk
        half_date_frames: int = int((RENDER_FRAME_RATE * DURATION_DATE_SEC + 1) / 2)
        if self.frame_num < half_date_frames:
            market_radius *= self.frame_num / half_date_frames
        else:
            market_radius *= (RENDER_FRAME_RATE * DURATION_DATE_SEC - self.frame_num) / half_date_frames
        return INDUSTRY_MIN_FATNESS + market_radius


class RenderFadeInRepository:
    def __init__(self):
        self.events: typing.List[RenderFadeInEvent] = []
        self.__killmails: typing.List[RenderFadeInKillmail] = []
        self.industry: typing.List[RenderFadeInIndustry] = []
        self.market: typing.List[RenderFadeInMarket] = []

    def add_event(self, item: RenderFadeInEvent):
        if len(self.events) == NUMBER_OF_EVENTS:
            del self.events[NUMBER_OF_EVENTS-1]
        self.events.insert(0, item)

    def add_killmail(self, item: RenderFadeInKillmail):
        self.__killmails.insert(0, item)

    def add_industry(self, item: RenderFadeInIndustry):
        self.industry.append(item)

    def add_market(self, item: RenderFadeInMarket):
        self.market.append(item)

    @property
    def killmails_in_list(self):
        return [k for k in self.__killmails if k.show_in_list]

    @property
    def killmails_on_map(self):
        return [k for k in self.__killmails if k.show_on_map]

    def pass_frame(self):
        # уменьшаем яркость events-надписей и удаляем ставшие практически прозрачными
        list_of_disappeared_events: typing.List[int] = []
        for (idx, e) in enumerate(self.events):
            e.pass_frame()
            if e.disappeared:
                list_of_disappeared_events.insert(0, idx)
        for idx in list_of_disappeared_events:
            del self.events[idx]
        # уменьшаем яркость killmails-надписей и удаляем ставшие практически прозрачными
        list_of_disappeared_killmails: typing.List[int] = []
        for (idx, k) in enumerate(self.__killmails):
            k.pass_frame()
            if k.disappeared:
                list_of_disappeared_killmails.insert(0, idx)
        for idx in list_of_disappeared_killmails:
            del self.__killmails[idx]
        # уменьшаем яркость industry-надписей и удаляем ставшие практически прозрачными
        list_of_disappeared_industry: typing.List[int] = []
        for (idx, i) in enumerate(self.industry):
            i.pass_frame()
            if i.disappeared:
                list_of_disappeared_industry.insert(0, idx)
        for idx in list_of_disappeared_industry:
            del self.industry[idx]
        # уменьшаем яркость industry-надписей и удаляем ставшие практически прозрачными
        list_of_disappeared_market: typing.List[int] = []
        for (idx, m) in enumerate(self.market):
            m.pass_frame()
            if m.disappeared:
                list_of_disappeared_market.insert(0, idx)
        for idx in list_of_disappeared_market:
            del self.market[idx]


class RenderUniverse:
    def __init__(
            self,
            canvas: Image,
            img_draw: ImageDraw,
            scale: RenderScale,
            date_font: ImageFont,
            events_font: ImageFont,
            killmails_font: ImageFont):
        self.canvas = canvas
        self.img_draw = img_draw
        self.scale = scale
        self.date_font = date_font
        self.events_font = events_font
        self.killmails_font = killmails_font

    @staticmethod
    def create_transparent_ellipse(radius: float, blur_size: int, color: (int, int, int), alpha: int):
        # считаем размер изображения (закладываем границу для размытия края круга)
        border_width: int = blur_size + 3
        img_size: (int, int) = (2 * int(radius + 0.99 + border_width), 2 * int(radius + 0.99 + border_width))
        # рисуем на чёрном фоне белый круг - это будет маска изображения
        mask = Image.new("L", img_size, 0)
        ImageDraw.Draw(mask).ellipse(
            (border_width, border_width, border_width + int(2 * radius), border_width + int(2 * radius)), fill=alpha)
        img_mask_blur = mask.filter(ImageFilter.GaussianBlur(blur_size))
        del mask
        # создаём изображение - красное полотно, на которое накладываем маску с кругом => прозрачный красный круг
        transp_img = Image.new('RGB', img_size, color)
        transp_img.putalpha(img_mask_blur)
        del img_mask_blur
        return transp_img

    def draw_solar_system(self, x: float, z: float, luminosity: float):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        __fatness: float = SOLAR_SYSTEM_FATNESS
        __luminosity: int = int(LUMINOSITY_MIN_BOUND + (sqrt(luminosity) - self.scale.min_luminosity) * self.scale.scale_luminosity)
        __shape = [(__x - __fatness, __z - __fatness), (__x + __fatness, __z + __fatness)]
        self.img_draw.ellipse(__shape, fill=(__luminosity, __luminosity, __luminosity))

    def highlight_solar_system(self, x: float, z: float, color: (int, int, int), fatness: float, alpha: int):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        # DEBUG: print("{}x{} {} {} {}".format(int(__x), int(__z), color, fatness, alpha))
        transp_img: Image = self.create_transparent_ellipse(fatness, 4, color, alpha)
        shift: (int, int) = transp_img.size
        shift = (int(__x - shift[0]/2), int(__z - shift[1]/2))
        self.canvas.paste(transp_img, shift, transp_img)
        del transp_img

    def draw_events_list(self, events: typing.List[RenderFadeInEvent]):
        __x: int = self.scale.left_bound_of_events
        for (idx, e) in enumerate(events):
            __y: float = RENDER_HEIGHT - idx*RENDER_HEIGHT/NUMBER_OF_EVENTS - self.scale.fontsize
            self.img_draw.text((__x, __y), e.txt, fill=e.color, font=self.events_font)

    def draw_killmails_list(self, killmails: typing.List[RenderFadeInKillmail]):
        __x: int = 0  # self.scale.left_bound_of_events
        for (idx, k) in enumerate(killmails):
            if idx == NUMBER_OF_KILLMAILS_IN_LIST:
                break
            __y: float = RENDER_HEIGHT - idx*RENDER_HEIGHT/NUMBER_OF_EVENTS - self.scale.fontsize
            self.img_draw.text((__x, __y), k.txt, fill=k.list_color, font=self.events_font)

    def draw_killmails_map(self, killmails: typing.List[RenderFadeInKillmail]):
        for k in killmails:
            self.highlight_solar_system(k.x, k.z, k.map_color, k.map_radius, k.map_alpha)

    def draw_industry_map(self, industry: typing.List[RenderFadeInIndustry]):
        for i in industry:
            if i.x is not None:
                self.highlight_solar_system(i.x, i.z, i.map_color, i.map_radius, i.map_alpha)

    def draw_market_map(self, market: typing.List[RenderFadeInMarket]):
        for m in market:
            if m.x is not None:
                self.highlight_solar_system(m.x, m.z, m.map_color, m.map_radius, m.map_alpha)

    def draw_date_caption(self, date: str):
        __x: float = self.scale.render_center_width + (self.scale.min_x - self.scale.universe_center_x) * self.scale.scale_x
        self.img_draw.text((__x, 10), date, fill=(140, 140, 140), font=self.date_font)


def render_base_image(cwd: str, input_dir: str, out_dir: str, date_from: str, date_to: str, verbose: bool = False):
    sde_names = eve_sde_tools.read_converted(cwd, "invNames")
    if verbose:
        print("Read {} names in Universe".format(len(sde_names)))
    sde_positions = eve_sde_tools.read_converted(cwd, "fsdUniversePositions")
    if verbose:
        print("Read {} solar systems positions in Universe".format(len(sde_positions)))

    # рассчитываем пропорции и региона на изображении, которые будут использоваться для отрисовки разной информации
    render_scale = RenderScale()
    render_scale.calc(sde_positions)
    render_scale.choose_font_size()
    if verbose:
        print("Min and max positions:", render_scale.min_x, render_scale.max_x, render_scale.min_z, render_scale.max_z)
        print("Center positions:", render_scale.universe_center_x, render_scale.universe_center_z)
        print("Min and max luminosity:", render_scale.min_luminosity, render_scale.max_luminosity)
        print('Scale {} {} for {}x{} bitmap'.format(render_scale.scale_x, render_scale.scale_z, RENDER_WIDTH, RENDER_HEIGHT))
        print('Rectangle of universe in bitmap {} x {} : {} x {}'.format(
            render_scale.render_center_width + (render_scale.min_x-render_scale.universe_center_x)*render_scale.scale_x,
            render_scale.render_half_height - (render_scale.min_z-render_scale.universe_center_z)*render_scale.scale_z,
            render_scale.render_center_width + (render_scale.max_x-render_scale.universe_center_x)*render_scale.scale_x,
            render_scale.render_half_height - (render_scale.max_z-render_scale.universe_center_z)*render_scale.scale_z))
        print('Scale {} of luminosity for min {} and max {}'.format(
            render_scale.scale_luminosity,
            LUMINOSITY_MIN_BOUND+render_scale.min_luminosity*render_scale.scale_luminosity,
            LUMINOSITY_MIN_BOUND+(render_scale.max_luminosity-render_scale.min_luminosity)*render_scale.scale_luminosity))
    # настраиваем шрифты, которым будем рисовать события даты и т.п.
    events_font = ImageFont.truetype("arial.ttf", render_scale.fontsize)
    date_font = ImageFont.truetype("arial.ttf", render_scale.fontsize)

    start_date = datetime.datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
    stop_date = datetime.datetime.strptime(date_to, '%Y-%m-%d') if date_to else None

    # читаем данные из файлов
    events_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_EVENTS_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_EVENTS_COL_DATE], '%Y-%m-%d')
            if start_date and stop_date and (start_date <= dt <= stop_date) or start_date and (start_date <= dt) or \
               stop_date and (stop_date <= dt) or not start_date and not stop_date:
                events_with_dates.append(row)
        del reader
    # ---
    killmails_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_KILLMAILS_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_KILLMAILS_COL_DATE], '%Y-%m-%d')
            if start_date and stop_date and (start_date <= dt <= stop_date) or start_date and (start_date <= dt) or \
               stop_date and (stop_date <= dt) or not start_date and not stop_date:
                killmails_with_dates.append(row)
        del reader
    # ---
    industry_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_INDUSTRY_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_INDUSTRY_COL_DATE], '%Y-%m-%d')
            if start_date and stop_date and (start_date <= dt <= stop_date) or start_date and (start_date <= dt) or \
               stop_date and (stop_date <= dt) or not start_date and not stop_date:
                industry_with_dates.append(row)
        del reader
    # ---
    market_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_MARKET_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_MARKET_COL_DATE], '%Y-%m-%d')
            if start_date and stop_date and (start_date <= dt <= stop_date) or start_date and (start_date <= dt) or \
               stop_date and (stop_date <= dt) or not start_date and not stop_date:
                market_with_dates.append(row)
        del reader

    # определяем диапазон дат, которые будут участвовать в создании кадров
    if start_date:
        render_date = start_date
    else:
        dts: typing.List[str] = []
        if events_with_dates:
            dts.append(events_with_dates[0][FILE_EVENTS_COL_DATE])
        if killmails_with_dates:
            dts.append(killmails_with_dates[0][FILE_KILLMAILS_COL_DATE])
        if industry_with_dates:
            dts.append(industry_with_dates[0][FILE_INDUSTRY_COL_DATE])
        if market_with_dates:
            dts.append(market_with_dates[0][FILE_MARKET_COL_DATE])
        render_date = None
        for dt in dts:
            dtd = datetime.datetime.strptime(dt, '%Y-%m-%d')
            if render_date is None or render_date > dtd:
                render_date = dtd

    if not stop_date:
        dtf: typing.List[str] = []
        if events_with_dates:
            dtf.append(events_with_dates[-1][FILE_EVENTS_COL_DATE])
        if killmails_with_dates:
            dtf.append(killmails_with_dates[-1][FILE_KILLMAILS_COL_DATE])
        if industry_with_dates:
            dtf.append(industry_with_dates[-1][FILE_INDUSTRY_COL_DATE])
        if market_with_dates:
            dtf.append(market_with_dates[-1][FILE_MARKET_COL_DATE])
        stop_date = None
        for dt in dtf:
            dtd = datetime.datetime.strptime(dt, '%Y-%m-%d')
            if stop_date is None or stop_date < dtd:
                stop_date = dtd

    if verbose:
        print('Loaded {} events, {} killmails, {} jobs, {} markets'.format(
            len(events_with_dates),
            len(killmails_with_dates),
            len(industry_with_dates),
            len(market_with_dates)
        ))
        print('Date from {} and date to {} choosen'.format(render_date, stop_date))

    # набор данных, которые подвергаются мерцанию и переменные для статистики
    render_fade_in: RenderFadeInRepository = RenderFadeInRepository()
    maximum_num_of_industry_jobs = 0
    maximum_isk_per_day = 0

    # номер фрейма, который задаёт имя файла и последовательно используется ffmpeg-программой
    image_index: int = 0
    while True:
        # получаем дату "сегодняшнего дня"
        render_date_str: str = datetime.datetime.strftime(render_date, '%Y-%m-%d')
        if verbose:
            print('==', render_date_str)
        # добавляем события "сегодняшнего дня" в список отрисовки
        if events_with_dates:
            num_new_events: int = 0
            while render_date_str == events_with_dates[0][FILE_EVENTS_COL_DATE]:
                e: RenderFadeInEvent = RenderFadeInEvent(
                    events_with_dates[0][FILE_EVENTS_COL_TXT],
                    int(events_with_dates[0][FILE_EVENTS_COL_LEVEL]))
                render_fade_in.add_event(e)
                num_new_events += 1
                del events_with_dates[0]
                if not events_with_dates:
                    break
            if verbose and num_new_events:
                print(' {} new events'.format(num_new_events))
        if killmails_with_dates:
            num_new_killmails: int = 0
            while render_date_str == killmails_with_dates[0][FILE_KILLMAILS_COL_DATE]:
                p = sde_positions.get(killmails_with_dates[0][FILE_KILLMAILS_COL_SYSTEM])
                k: RenderFadeInKillmail = RenderFadeInKillmail(
                    killmails_with_dates[0][FILE_KILLMAILS_COL_VICTIM] == '1',
                    killmails_with_dates[0][FILE_KILLMAILS_COL_TXT],
                    int(killmails_with_dates[0][FILE_KILLMAILS_COL_SHIPTYPE]),
                    float(killmails_with_dates[0][FILE_KILLMAILS_COL_MASS]),
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_killmail(k)
                num_new_killmails += 1
                del killmails_with_dates[0]
                if not killmails_with_dates:
                    break
            if verbose and num_new_killmails:
                print(' {} new killmails'.format(num_new_killmails))
        if industry_with_dates:
            num_new_industry_jobs: int = 0
            while render_date_str == industry_with_dates[0][FILE_INDUSTRY_COL_DATE]:
                p = sde_positions.get(industry_with_dates[0][FILE_INDUSTRY_COL_SYSTEM])
                k: RenderFadeInIndustry = RenderFadeInIndustry(
                    int(industry_with_dates[0][FILE_INDUSTRY_COL_JOBS]),
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_industry(k)
                num_new_industry_jobs += int(industry_with_dates[0][FILE_INDUSTRY_COL_JOBS])
                del industry_with_dates[0]
                if not industry_with_dates:
                    break
            if verbose and num_new_industry_jobs:
                print(' {} new industry stat'.format(num_new_industry_jobs))
            if num_new_industry_jobs > maximum_num_of_industry_jobs:
                maximum_num_of_industry_jobs = num_new_industry_jobs
                e: RenderFadeInEvent = RenderFadeInEvent(
                    'Industry achievement , {} jobs'.format(maximum_num_of_industry_jobs),
                    3)
                render_fade_in.add_event(e)
        if market_with_dates:
            sum_isk_per_day: int = 0
            while render_date_str == market_with_dates[0][FILE_MARKET_COL_DATE]:
                p = sde_positions.get(market_with_dates[0][FILE_MARKET_COL_SYSTEM])
                k: RenderFadeInMarket = RenderFadeInMarket(
                    float(market_with_dates[0][FILE_MARKET_COL_ISK]),
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_market(k)
                sum_isk_per_day += int(float(market_with_dates[0][FILE_MARKET_COL_ISK]))
                del market_with_dates[0]
                if not market_with_dates:
                    break
            if verbose and sum_isk_per_day:
                print(' {} ISK in market operations'.format(sum_isk_per_day))
            if sum_isk_per_day > maximum_isk_per_day:
                maximum_isk_per_day = sum_isk_per_day
                e: RenderFadeInEvent = RenderFadeInEvent(
                    'Market achievement, {:,d} ISK'.format(maximum_isk_per_day),
                    4)
                render_fade_in.add_event(e)

        # ---
        for frame_idx in range(DURATION_DATE):
            # создаём канву на которой будем рисовать
            canvas = Image.new('RGB', (RENDER_WIDTH, RENDER_HEIGHT), 'black')
            img_draw = ImageDraw.Draw(canvas, 'RGB')
            # DEBUG: img_draw.rectangle((0, 0, 400, 400), fill='#646D7E')

            # генерируем рисовалку вселенной и корпоративных событий
            renderer: RenderUniverse = RenderUniverse(canvas, img_draw, render_scale, date_font, events_font, events_font)
            # генерируем базовый фон с нанесёнными на него звёздами Вселенной EVE
            for p in sde_positions.values():
                renderer.draw_solar_system(p[0], p[2], p[3])
            # наносим дату на изображение
            renderer.draw_date_caption(render_date_str)
            # наносим на изображение надписи и тушим на их на шаг прозрачности
            renderer.draw_events_list(render_fade_in.events)
            renderer.draw_killmails_list(render_fade_in.killmails_in_list)
            # наносим на изображение места гибели кораблей
            renderer.draw_killmails_map(render_fade_in.killmails_on_map)
            # наносим на изображение производственные фабрики
            renderer.draw_industry_map(render_fade_in.industry)
            # наносим на изображение рыночные сделки
            renderer.draw_market_map(render_fade_in.market)
            # событиям, находящимся в репозитории "затухания" повышается прозрачность
            render_fade_in.pass_frame()

            # canvas.save('{}/{}_{:0>3}.png'.format(out_dir, render_date_str, frame_idx))
            canvas.save('{}/{:0>5}.png'.format(out_dir, image_index))
            image_index += 1
            # canvas.show()

        del img_draw
        del canvas
        # ---
        if render_date == stop_date:
            break
        render_date += datetime.timedelta(days=1)

    del sde_positions
    del sde_names
