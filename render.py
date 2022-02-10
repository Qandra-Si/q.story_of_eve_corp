import typing
from math import sqrt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import csv

import eve_sde_tools
import render_settings


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
        self.render_center_width: float = 0.0
        self.render_half_height: float = 0.0
        self.scale_x: float = 0.0
        self.scale_z: float = 0.0
        self.scale_luminosity: float = 0.0
        # размер шрифтов для рисования надписей на картинке
        self.fontsize = 1
        self.left_bound_of_events: int = 0
        self.top_bound_of_events: int = 0
        self.bottom_bound_of_events: int = 0
        # позиция вывода даты
        self.right_bound_of_date: int = 8
        self.top_bound_of_date: int = 8
        # поправки для региона отображения списка пилотов
        self.right_bound_of_pilots: int = 0
        self.left_bound_of_pilots: int = 8
        self.top_bound_of_pilots: int = 8
        self.bottom_bound_of_pilots: typing.Optional[int] = 0  # вычисляется после нанесения списка пилотов на экран

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
        self.scale_z = render_settings.RENDER_HEIGHT / self.universe_height
        self.scale_x = render_settings.RENDER_HEIGHT / self.universe_width
        # рассчитываем положение карты (может быть либо по центру, либо справа)
        if render_settings.RENDER_LAYOUT == render_settings.RenderLayout.MAP_CENTER:
            # render_half_height выполняет роль стороны квадрата, куда будут вписаны SS
            self.render_center_width = render_settings.RENDER_WIDTH / 2.0
            self.render_half_height = render_settings.RENDER_HEIGHT / 2.0
            # рассчитываем позицию региона, где будут появляться события
            self.left_bound_of_events = int(self.render_center_width + (self.max_x - self.universe_center_x) * self.scale_x) + 20
            self.top_bound_of_events = 8
            self.bottom_bound_of_events = render_settings.RENDER_HEIGHT - 8
            # рассчитываем позицию региона в датой
            self.right_bound_of_date = self.left_bound_of_events - 20
            # считаем позицию региона со списком пилотов (сдвигаем границу внутрь карты, т.к. вверху она полупустая)
            self.right_bound_of_pilots = int( self.render_center_width + (self.min_x - self.universe_center_x) / 3 * self.scale_x)
        elif render_settings.RENDER_LAYOUT == render_settings.RenderLayout.MAP_RIGHT:
            self.render_center_width = render_settings.RENDER_WIDTH - (self.max_x-self.universe_center_x)*self.scale_x
            self.render_half_height = render_settings.RENDER_HEIGHT / 2.0
            # рассчитываем позицию региона, где будут появляться события
            self.left_bound_of_events = 8
            self.top_bound_of_events = None  # зависит от высоты блока со списком пилотов
            self.bottom_bound_of_events = render_settings.RENDER_HEIGHT - 8  # зависит от высоты блока с killmails
            # рассчитываем позицию региона в датой
            self.right_bound_of_date = render_settings.RENDER_WIDTH - 8
            # считаем позицию региона со списком пилотов (сдвигаем границу внутрь карты, т.к. вверху она полупустая)
            self.right_bound_of_pilots = int( self.render_center_width + (self.min_x - self.universe_center_x) * self.scale_x)
        else:
            raise Exception("Unsupported map layout setup")
        # расчёт светимости, берём мощность от яркости, как корень квадратный
        self.min_luminosity = sqrt(self.min_luminosity)
        self.max_luminosity = sqrt(self.max_luminosity)
        self.scale_luminosity = (render_settings.LUMINOSITY_MAX_BOUND - render_settings.LUMINOSITY_MIN_BOUND) / (self.max_luminosity - self.min_luminosity)

    @staticmethod
    def calc_font_size(lines_count: int) -> int:
        fontsize: int = 10  # начальный размер шрифта
        font = ImageFont.truetype("arial.ttf", fontsize)
        # итерируемся по размерам шрифтов так, чтобы в высоту изображения влезло N строк
        height: int = render_settings.RENDER_HEIGHT - 8 - 8
        while font.getsize("Qandra Si")[1] < (height / lines_count):
            fontsize += 1
            font = ImageFont.truetype("arial.ttf", fontsize)
        del font
        # опционально уменьшаем размер шрифта, чтобы была верхние надписи не уходили за экран (впрочем они там и так
        # затухают, т.ч. это действительно необязательно)
        # self.fontsize -= 1
        return fontsize

    def choose_font_size(self):
        self.fontsize =self.calc_font_size(render_settings.NUMBER_OF_EVENTS)


class RenderFadeInEvent:
    def __init__(self, txt: str, level: int):
        self.txt: str = txt
        self.__color: (int, int, int) = render_settings.EVENTS_SETUP[level][0]
        self.opacity: float = 1.0
        self.frame_num: int = 1
        self.lifetime_frames: int = render_settings.EVENTS_SETUP[level][1] * render_settings.RENDER_FRAME_RATE
        self.transparency_frame: float = 1.0 / self.lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.frame_num += 1
        self.opacity -= self.transparency_frame
        if self.opacity < 0.0:
            self.opacity = 0.0

    @property
    def color(self) -> (int, int, int):
        return int(self.__color[0] * self.opacity), int(self.__color[1] * self.opacity), int(self.__color[2] * self.opacity)

    @property
    def disappeared(self) -> bool:
        return self.frame_num > self.lifetime_frames


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
        self.__color: typing.Optional[(int, int, int)] = render_settings.KILLMAILS_SETUP[self.__level][0]
        self.txt: str = txt
        self.mass: float = ship_mass
        self.x: typing.Optional[float] = x
        self.z: typing.Optional[float] = z
        self.frame_num: int = 1
        map_days: int = render_settings.KILLMAILS_SETUP[self.__level][1]
        self.map_lifetime_frames: int = map_days * render_settings.RENDER_FRAME_RATE
        self.map_opacity: float = 1.0
        self.map_transparency_frame: float = 1.0 / self.map_lifetime_frames  # мера прозрачности, добавляемая каждый фрейм
        if render_settings.KILLMAILS_SETUP[self.__level][2] is None:
            self.list_lifetime_frames = None
        else:
            list_days: float = self.__get_boom_metrix()
            if list_days < (map_days + 1):
                list_days = (map_days + 1)
            else:
                list_days = min(list_days, render_settings.KILLMAILS_SETUP[self.__level][2])
            self.list_lifetime_frames = list_days * render_settings.RENDER_FRAME_RATE
            self.list_opacity: float = 1.0
            self.list_transparency_frame: float = 1.0 / self.list_lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.frame_num += 1
        self.map_opacity -= self.map_transparency_frame
        if self.map_opacity < 0.0:
            self.map_opacity = 0.0
        if self.list_lifetime_frames is not None:
            self.list_opacity -= self.list_transparency_frame
            if self.list_opacity < 0.0:
                self.list_opacity = 0.0

    @property
    def show_in_list(self) -> bool:
        return self.list_lifetime_frames is not None

    @property
    def show_on_map(self) -> bool:
        return self.x is not None and self.frame_num <= self.map_lifetime_frames

    @property
    def disappeared(self) -> bool:
        if self.list_lifetime_frames is not None:
            return self.frame_num > self.list_lifetime_frames or self.list_opacity < 0.08
        else:
            return self.frame_num > self.map_lifetime_frames

    @property
    def list_color(self) -> (int, int, int):
        return int(self.__color[0] * self.list_opacity), int(self.__color[1] * self.list_opacity), int(self.__color[2] * self.list_opacity)

    @property
    def map_color(self) -> (int, int, int):
        return self.__color

    @property
    def map_alpha(self) -> int:
        return int(render_settings.KILLMAIL_MAP_MIN_ALPHA + (1.0-self.map_opacity) * (render_settings.KILLMAIL_MAP_MAX_ALPHA - render_settings.KILLMAIL_MAP_MIN_ALPHA))

    def __get_boom_metrix(self) -> float:
        # Customs Office  mass = 5'000'000'000  sqrt = 70'710
        # Astrahus        mass = 3'000'000'000  sqrt = 54'772
        # Rhea            mass =   960'000'000  sqrt = 30'983
        # Bhaalgorn       mass =    97'100'000  sqrt =  9'853
        # Venture         mass =     1'200'000  sqrt =  1'095
        # Capsule         mass =        32'000  sqrt =    178
        boom_metrix: float = sqrt(self.mass) / 1000.0  # раньше было mass / 50000000
        return boom_metrix

    @property
    def map_radius(self) -> float:
        # в первые треть игровых суток радиус взрыва растёт, пока на достигнет эквивалента массы
        # Astrahus 3'000'000'000, Rhea 960'000'000, Capsule 32'000, Venture 1'200'000
        boom_radius: float = self.__get_boom_metrix()
        if boom_radius < render_settings.KILLMAIL_MIN_FATNESS:
            boom_radius = render_settings.KILLMAIL_MIN_FATNESS
        growing_frames: int = int((render_settings.DURATION_DATE + 1) / 3)
        if self.frame_num < growing_frames:
            boom_radius *= self.frame_num / growing_frames
        # радиус взрыва делаем не меньше чем радиус солнечной системы
        if boom_radius < render_settings.SOLAR_SYSTEM_FATNESS:
            boom_radius = render_settings.SOLAR_SYSTEM_FATNESS
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
        self.transparency_frame: float = 2.0 / render_settings.DURATION_DATE  # мера прозрачности, добавляемая каждый фрейм
        self.opacity: float = 0.0

    def pass_frame(self):
        self.frame_num += 1
        if self.frame_num < (render_settings.DURATION_DATE + 1) / 2:
            self.opacity += self.transparency_frame
            if self.opacity > 1.0:
                self.opacity = 1.0
        else:
            self.opacity -= self.transparency_frame
            if self.opacity < 0.0:
                self.opacity = 0.0

    @property
    def disappeared(self) -> bool:
        return self.frame_num > render_settings.DURATION_DATE

    @property
    def map_color(self) -> (int, int, int):
        return render_settings.INDUSTRY_SETUP

    @property
    def map_alpha(self) -> int:
        return int(render_settings.INDUSTRY_MAP_MIN_ALPHA + (1.0-self.opacity) * (render_settings.INDUSTRY_MAP_MAX_ALPHA - render_settings.INDUSTRY_MAP_MIN_ALPHA))

    @property
    def map_radius(self) -> float:
        industry_radius: float = 13 * self.runs / 1000  # 2022-02-02 : 2581 работ
        half_date_frames: int = int((render_settings.DURATION_DATE + 1) / 2)
        if self.frame_num < half_date_frames:
            industry_radius *= self.frame_num / half_date_frames
        else:
            industry_radius *= (render_settings.DURATION_DATE - self.frame_num) / half_date_frames
        return render_settings.INDUSTRY_MIN_FATNESS + industry_radius


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
        self.transparency_frame: float = 2.0 / render_settings.DURATION_DATE  # удвоенная мера прозрачности, добавляемая каждый фрейм
        self.opacity: float = 0.0

    def pass_frame(self):
        self.frame_num += 1
        if self.frame_num < (render_settings.DURATION_DATE + 1) / 2:
            self.opacity += self.transparency_frame
            if self.opacity > 1.0:
                self.opacity = 1.0
        else:
            self.opacity -= self.transparency_frame
            if self.opacity < 0.0:
                self.opacity = 0.0

    @property
    def disappeared(self) -> bool:
        return self.frame_num > render_settings.DURATION_DATE

    @property
    def map_color(self) -> (int, int, int):
        return render_settings.MARKET_SETUP

    @property
    def map_alpha(self) -> int:
        return int(render_settings.MARKET_MAP_MIN_ALPHA + (1.0-self.opacity) * (render_settings.MARKET_MAP_MAX_ALPHA - render_settings.MARKET_MAP_MIN_ALPHA))

    @property
    def map_radius(self) -> float:
        market_radius: float = 13 * self.isk / 20000000000  # 2021-12-09 : 74'161'872'333 isk
        half_date_frames: int = int((render_settings.DURATION_DATE + 1) / 2)
        if self.frame_num < half_date_frames:
            market_radius *= self.frame_num / half_date_frames
        else:
            market_radius *= (render_settings.DURATION_DATE - self.frame_num) / half_date_frames
        return render_settings.MARKET_MIN_FATNESS + market_radius


class RenderFadeInRegion:
    def __init__(self, region_id: int, color: (int, int, int) = None):
        self.region_id: int = region_id
        self.__color: (int, int, int) = render_settings.REGION_SETUP[0] if not color else color
        self.opacity: float = 1.0
        self.frame_num: int = 1
        self.lifetime_frames: int = render_settings.REGION_SETUP[1] * render_settings.RENDER_FRAME_RATE
        self.transparency_frame: float = 1.0 / self.lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.frame_num += 1
        self.opacity -= self.transparency_frame
        if self.opacity < 0.0:
            self.opacity = 0.0

    @property
    def color(self) -> (int, int, int):
        return int(self.__color[0] * self.opacity), int(self.__color[1] * self.opacity), int(self.__color[2] * self.opacity)

    @property
    def disappeared(self) -> bool:
        return self.frame_num > self.lifetime_frames


class RenderFadeInRepository:
    def __init__(self):
        self.events: typing.List[RenderFadeInEvent] = []
        self.__killmails: typing.List[RenderFadeInKillmail] = []
        self.industry: typing.List[RenderFadeInIndustry] = []
        self.market: typing.List[RenderFadeInMarket] = []
        self.regions: typing.List[RenderFadeInRegion] = []

    def add_event(self, item: RenderFadeInEvent):
        if len(self.events) == render_settings.NUMBER_OF_EVENTS:
            del self.events[render_settings.NUMBER_OF_EVENTS-1]
        self.events.insert(0, item)

    def add_killmail(self, item: RenderFadeInKillmail):
        self.__killmails.insert(0, item)

    def add_industry(self, item: RenderFadeInIndustry):
        self.industry.append(item)

    def add_market(self, item: RenderFadeInMarket):
        self.market.append(item)

    def add_region(self, item: RenderFadeInRegion):
        self.regions.append(item)

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
        # уменьшаем яркость region-надписей и удаляем ставшие практически прозрачными
        list_of_disappeared_regions: typing.List[int] = []
        for (idx, r) in enumerate(self.regions):
            r.pass_frame()
            if r.disappeared:
                list_of_disappeared_regions.insert(0, idx)
        for idx in list_of_disappeared_regions:
            del self.regions[idx]


class RenderPilots:
    def __init__(
            self,
            employment_with_dates: typing.List[typing.Any],
            pilot_img: Image,
            pilot_contour_img: Image):
        # иконки для рисования пилотов
        self.pilot_img = pilot_img
        self.pilot_contour_img = pilot_contour_img
        # ПОЛУПРОЗРАЧНЫЕ иконки для рисования пилотов
        __pilot_img = Image.new('RGB', self.pilot_img.size, 0)
        __pilot_img.paste(self.pilot_img, (0, 0), self.pilot_img)
        __pilot_contour_img = Image.new('RGB', self.pilot_contour_img.size, 0)
        __pilot_contour_img.paste(self.pilot_contour_img, (0, 0), self.pilot_contour_img)
        # ---
        self.pilot_1st = __pilot_img.copy()
        self.pilot_1st.putalpha(0x33)
        self.pilot_2nd = __pilot_img.copy()
        self.pilot_2nd.putalpha(0x66)
        self.pilot_3rd = __pilot_img.copy()
        self.pilot_3rd.putalpha(0x99)
        self.pilot_4th = __pilot_img.copy()
        self.pilot_4th.putalpha(0xcc)
        # ---
        self.contour_img_1st = __pilot_contour_img.copy()
        self.contour_img_1st.putalpha(0x33)
        self.contour_img_2nd = __pilot_contour_img.copy()
        self.contour_img_2nd.putalpha(0x66)
        self.contour_img_3rd = __pilot_contour_img.copy()
        self.contour_img_3rd.putalpha(0x99)
        self.contour_img_4th = __pilot_contour_img.copy()
        self.contour_img_4th.putalpha(0xcc)
        # коллекция пилотов (их идентификаторов) для отслеживания активности в корпорации
        self.pilots: typing.List[typing.Any] = employment_with_dates


class RenderUniverse:
    def __init__(
            self,
            canvas: Image,
            img_draw: ImageDraw,
            scale: RenderScale,
            date_font: ImageFont,
            events_font: ImageFont,
            killmails_font: ImageFont,
            region_font: ImageFont):
        self.canvas: Image = canvas
        self.img_draw: ImageDraw = img_draw
        self.scale: RenderScale = scale
        self.date_font: ImageFont = date_font
        self.events_font: ImageFont = events_font
        self.killmails_font: ImageFont = killmails_font
        self.region_font: ImageFont = region_font

    @staticmethod
    def create_transparent_ellipse(radius: float, blur_size: int, color: (int, int, int), alpha: int):
        # считаем размер изображения (закладываем границу для размытия края круга)
        border_width: int = blur_size + 3
        img_size: (int, int) = (2 * int(radius + 0.99 + border_width), 2 * int(radius + 0.99 + border_width))
        # рисуем на чёрном фоне белый круг - это будет маска изображения
        mask = Image.new("L", img_size, 0)
        ImageDraw.Draw(mask).ellipse(
            (border_width, border_width, border_width + int(2 * radius), border_width + int(2 * radius)), fill=alpha)
        # создаём изображение - красное полотно, на которое накладываем маску с кругом => прозрачный красный круг
        transp_img = Image.new('RGB', img_size, color)
        if blur_size:
            img_mask_blur = mask.filter(ImageFilter.GaussianBlur(blur_size))
            transp_img.putalpha(img_mask_blur)
            del img_mask_blur
        else:
            transp_img.putalpha(mask)
        del mask
        return transp_img

    def draw_solar_system(self, x: float, z: float, luminosity: float):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        __fatness: float = render_settings.SOLAR_SYSTEM_FATNESS
        __luminosity: int = int(render_settings.LUMINOSITY_MIN_BOUND + (sqrt(luminosity) - self.scale.min_luminosity) * self.scale.scale_luminosity)
        transp_img: Image = self.create_transparent_ellipse(__fatness, render_settings.SOLAR_SYSTEM_BLUR, 'white', __luminosity)
        shift: (int, int) = transp_img.size
        shift = (int(__x - shift[0] / 2), int(__z - shift[1] / 2))
        self.canvas.paste(transp_img, shift, transp_img)

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
        if render_settings.RENDER_LAYOUT == render_settings.RenderLayout.MAP_CENTER:
            __y: float = self.scale.bottom_bound_of_events - self.scale.fontsize
            for e in events:
                self.img_draw.text((__x, __y), e.txt, fill=e.color, font=self.events_font)
                __y -= self.scale.fontsize
        elif render_settings.RENDER_LAYOUT == render_settings.RenderLayout.MAP_RIGHT:
            __y: float = self.scale.top_bound_of_events
            for e in events:
                self.img_draw.text((__x, __y), e.txt, fill=e.color, font=self.events_font)
                __y += self.scale.fontsize

    def draw_killmails_list(self, killmails: typing.List[RenderFadeInKillmail]):
        __x: int = 0  # self.scale.left_bound_of_events
        __height: float = render_settings.RENDER_HEIGHT - 8
        for (idx, k) in enumerate(killmails):
            __y: float = __height - idx*__height/render_settings.NUMBER_OF_EVENTS - self.scale.fontsize
            if __y < self.scale.bottom_bound_of_pilots:
                break
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
        left: int = self.scale.right_bound_of_date - self.date_font.getsize(date)[0]
        # внизу: top: int = render_settings.RENDER_HEIGHT - self.scale.bottom_bound_of_date - self.scale.fontsize
        top: int = self.scale.top_bound_of_date  # вверху
        self.img_draw.text((left, top), date, fill=(140, 140, 140), font=self.date_font)

    def draw_pilots(self, pilots: RenderPilots, render_date: datetime.datetime, transparency: float):
        width: int = pilots.pilot_1st.width + 4
        height: int = pilots.pilot_1st.height + 4
        right_bound: int = self.scale.right_bound_of_pilots - width
        # ---
        x: int = self.scale.left_bound_of_pilots
        y: int = self.scale.top_bound_of_pilots
        # ---
        main_pilot_id: typing.Optional[int] = None
        for p in pilots.pilots:
            main: int = p.main_id
            enter: datetime.date = p.enter_date
            gone: typing.Optional[datetime.date] = p.gone_date
            if enter <= render_date and (gone is None or render_date <= gone):
                # выбор картинок, которыми будем пользоваться
                if enter == render_date or (gone and gone == render_date):
                    if transparency < 0.25:
                        fill, contour = pilots.pilot_1st, pilots.contour_img_1st
                    elif transparency < 0.5:
                        fill, contour = pilots.pilot_2nd, pilots.contour_img_2nd
                    elif transparency < 0.75:
                        fill, contour = pilots.pilot_3rd, pilots.contour_img_3rd
                    else:  # if transparency < 0.8:
                        fill, contour = pilots.pilot_4th, pilots.contour_img_4th
                else:
                    fill, contour = pilots.pilot_img, pilots.pilot_contour_img
                # поскольку список отсортированный, то сбрасываем main-пилота как только он меняется
                if main_pilot_id and main_pilot_id != main:
                    main_pilot_id = None
                # рисуем в списке main-пилота (в данном случае важет только идентификатор, сам main в корпу
                # может войти позже - это зависит от того выбора, который сделал игрок)
                if main_pilot_id is None:
                    self.canvas.paste(fill, (x, y), fill)
                    main_pilot_id = main
                    x += width
                    if x >= right_bound:
                        x = self.scale.left_bound_of_pilots
                        y += height
                # рисуем в списке twink-пилота (и однократно main-пилота)
                self.canvas.paste(contour, (x, y), contour)
                x += width
                if x >= right_bound:
                    x = self.scale.left_bound_of_pilots
                    y += height
        # ---
        self.scale.bottom_bound_of_pilots = y + height
        self.scale.top_bound_of_events = self.scale.bottom_bound_of_pilots + 8

    def draw_regions(self, sde_regions: typing.Dict[str, typing.Any], regions: typing.List[RenderFadeInRegion]):
        for r in regions:
            sr = sde_regions.get(str(r.region_id))
            if sr is None:
                continue
            center: (float, float, float) = sr['center']
            x: float = self.scale.render_center_width + (center['x'] - self.scale.universe_center_x) * self.scale.scale_x
            y: float = self.scale.render_half_height - (center['z'] - self.scale.universe_center_z) * self.scale.scale_z
            sz: (int, int) = self.region_font.getsize(sr['name'])
            self.img_draw.text((x - sz[0]/2, y - sz[1]/2), sr['name'], fill=r.color, font=self.region_font)


class PlannedMapMovement:
    def __init__(
            self,
            date: datetime.date,
            ltx: float, lltx: int,
            ltz: float, lltz: int,
            rbx: float, lrbx: int,
            rbz: float, lrbz: int):
        self.date: datetime.date = date
        # сохраняем габариты группы регионов в которых происходят события
        self.left_x: float = ltx
        self.top_z: float = ltz
        self.right_x: float = rbx
        self.bottom_z: float = rbz
        # признаки фиксации габаритов групп регионов по соответствующим сторонам
        # если все признаки больше MOVEMENT_FREEZE_DURATION, то активности на карте не было и регион "продлён"
        # относительно предшествующих событий
        self.locked_minx: int = lltx
        self.locked_minz: int = lltz
        self.locked_maxx: int = lrbx
        self.locked_maxz: int = lrbz
        # признак того, что группа регионов "задержана" относительно предшествующих событий (подробнее см. locked_xxx)
        self.freezed: bool = False
        # готовим поля объекта, которые будут пересчитываться в динамике сравнением копий этих объектов по разным датам
        # (на каждом шаге преобразований пока алгоритм не готов полностью, стараемся сохранить полученные данные, для
        # того чтобы пользоваться отладкой по регионам карты)
        self.moved_minx: float = self.left_x
        self.moved_minz: float = self.top_z
        self.moved_maxx: float = self.right_x
        self.moved_maxz: float = self.bottom_z
        # расчёт перемещённых центров и рамок с сохранением пропорций видимой области будет завершён после коррекции
        # всех moved-полей
        self.width: typing.Optional[float] = None
        self.height: typing.Optional[float] = None
        self.center_x: typing.Optional[float] = None
        self.center_z: typing.Optional[float] = None
        self.corrected_minx: typing.Optional[float] = None
        self.corrected_minz: typing.Optional[float] = None
        self.corrected_maxx: typing.Optional[float] = None
        self.corrected_maxz: typing.Optional[float] = None

    def do_precise_calculation(self, render_scale: RenderScale):
        # рассчитываем местоположение центра группы регионов с событиями
        self.width: float = self.moved_maxx - self.moved_minx
        self.height: float = self.moved_maxz - self.moved_minz
        self.center_x = self.moved_minx + self.width / 2.0
        self.center_z = self.moved_minz + self.height / 2.0
        # рассчитываем пропорцию группы регионов с событиями по отношению к размеру карты (масштаб)
        map_proportion = render_scale.universe_width / render_scale.universe_height
        local_proportion: float = self.width / self.height
        if map_proportion > local_proportion:
            # группа регионов УЖЕ, надо её вписывать по высоте
            new_width: float = self.height * map_proportion
            self.width = new_width
            # при увеличении ширины области можем выехать за пределы карты слева или справа (корректируем центр)
            out_of_bounds_left: float = self.center_x - new_width/2 + render_scale.min_x
            if out_of_bounds_left > 0:
                self.center_x += out_of_bounds_left
            out_of_bounds_right: float = self.center_x + new_width/2 - render_scale.max_x
            if out_of_bounds_right > 0:
                self.center_x -= out_of_bounds_right
        else:
            # группа регионов ШИРЕ, надо её вписывать по ширине
            new_height: float = self.width / map_proportion
            self.height = new_height
            # при увеличении высоты области можем выехать за пределы карты сверху или снизу (корректируем центр)
            out_of_bounds_top: float = self.center_z - new_height/2 + render_scale.min_z
            if out_of_bounds_top > 0:
                self.center_z += out_of_bounds_top
            out_of_bounds_bottom: float = self.center_z + new_height/2 - render_scale.max_z
            if out_of_bounds_bottom > 0:
                self.center_z -= out_of_bounds_bottom
        # рассчитываем расположение left/right/top/bottom линий, откорректированных в процессе динамических коррекций
        self.corrected_minx = self.center_x - self.width/2
        self.corrected_minz = self.center_z - self.height/2
        self.corrected_maxx = self.center_x + self.width/2
        self.corrected_maxz = self.center_z + self.height/2

    """
    def __prolongate_not_freeze(self, date: datetime.date):
        copy: PlannedMapMovement = PlannedMapMovement(
            date,
            self.left_x, render_settings.MOVEMENT_FREEZE_DURATION + 1,
            self.top_z, render_settings.MOVEMENT_FREEZE_DURATION + 1,
            self.right_x, render_settings.MOVEMENT_FREEZE_DURATION + 1,
            self.bottom_z, render_settings.MOVEMENT_FREEZE_DURATION + 1)
        return copy
    """

    def prolongate(self, date: datetime.date):
        copy: PlannedMapMovement = PlannedMapMovement(
            date,
            self.left_x, self.locked_minx + 1,
            self.top_z, self.locked_minz + 1,
            self.right_x, self.locked_maxx + 1,
            self.bottom_z, self.locked_maxz + 1)
        return copy


class RenderRegionsActivity:
    def __init__(self, regions: typing.Dict[str, typing.Any]):
        self.regions: typing.Dict[str, typing.Any] = regions
        self.using: typing.Dict[int, datetime.date] = {}
        self.magnifier: typing.List[typing.Tuple[datetime.date, typing.Any]] = []
        self.rough_positions: typing.List[PlannedMapMovement] = []

    def draw_contours_of_regions_debug_only(self, img_draw: Image, scale: RenderScale, region_font: ImageFont):
        for region_id in self.using.keys():
            r = self.regions.get(str(region_id))
            """ контур """
            contour_min: (float, float, float) = r['min']
            contour_max: (float, float, float) = r['max']
            xmin: float = scale.render_center_width + (contour_min['x'] - scale.universe_center_x) * scale.scale_x - render_settings.SOLAR_SYSTEM_FATNESS
            zmin: float = scale.render_half_height - (contour_min['z'] - scale.universe_center_z) * scale.scale_z + render_settings.SOLAR_SYSTEM_FATNESS
            xmax: float = scale.render_center_width + (contour_max['x'] - scale.universe_center_x) * scale.scale_x + render_settings.SOLAR_SYSTEM_FATNESS
            zmax: float = scale.render_half_height - (contour_max['z'] - scale.universe_center_z) * scale.scale_z - render_settings.SOLAR_SYSTEM_FATNESS
            img_draw.rectangle((xmin+1, zmin-1, xmax-1, zmax+1), fill=None, outline='#333333', width=1)
            """ """
            contour_center: (float, float, float) = r['center']
            xcent: float = scale.render_center_width + (contour_center['x'] - scale.universe_center_x) * scale.scale_x
            zcent: float = scale.render_half_height - (contour_center['z'] - scale.universe_center_z) * scale.scale_z
            sz: (int, int) = region_font.getsize(r['name'])
            img_draw.text((xcent - sz[0]/2, zcent - sz[1]/2), r['name'], fill='#666', font=region_font)

    def draw_contours_of_magnifier_debug_only(self, img_draw: Image, scale: RenderScale, render_date: datetime.datetime):
        # увеличить контур региона на 1px: -1, +1, +1, -1
        # уменьшить контур региона на 1px: +1, -1, -1, +1
        # отрисовка областей с событиями с учётом пропорций карты и её видимой области на экране
        pdt = next((p for p in self.rough_positions if p.date == render_date), None)
        if pdt is not None:
            """
            center_x: float = scale.render_center_width + (pdt.center_x - scale.universe_center_x) * scale.scale_x
            center_z: float = scale.render_half_height - (pdt.center_z - scale.universe_center_z) * scale.scale_z
            width: float = pdt.width * scale.scale_x + 2 * render_settings.SOLAR_SYSTEM_FATNESS
            height: float = pdt.height * scale.scale_z + 2 * render_settings.SOLAR_SYSTEM_FATNESS
            img_draw.rectangle((center_x-width/2-2, center_z+height/2+2, center_x+width/2+2, center_z-height/2-2), fill=None, outline='#66FF00', width=1)
            """
            """
            # красный - ОТМАСШТАБИРОВАННАЯ ВИДИМАЯ область с учётом перемещений и коррекций пропорций
            xmin: float = scale.render_center_width + (pdt.corrected_minx - scale.universe_center_x) * scale.scale_x - render_settings.SOLAR_SYSTEM_FATNESS
            zmin: float = scale.render_half_height - (pdt.corrected_minz - scale.universe_center_z) * scale.scale_z + render_settings.SOLAR_SYSTEM_FATNESS
            xmax: float = scale.render_center_width + (pdt.corrected_maxx - scale.universe_center_x) * scale.scale_x + render_settings.SOLAR_SYSTEM_FATNESS
            zmax: float = scale.render_half_height - (pdt.corrected_maxz - scale.universe_center_z) * scale.scale_z - render_settings.SOLAR_SYSTEM_FATNESS
            img_draw.rectangle((xmin-3, zmin+3, xmax+3, zmax-3), fill=None, outline='#770000', width=1)
            """
            # малиновый - неотмасштабированная область в которой учтены ПЕРЕМЕЩЕНИЯ видимой области и СМЕЩЕНИЯ фокуса
            xmin: float = scale.render_center_width + (pdt.moved_minx - scale.universe_center_x) * scale.scale_x - render_settings.SOLAR_SYSTEM_FATNESS
            zmin: float = scale.render_half_height - (pdt.moved_minz - scale.universe_center_z) * scale.scale_z + render_settings.SOLAR_SYSTEM_FATNESS
            xmax: float = scale.render_center_width + (pdt.moved_maxx - scale.universe_center_x) * scale.scale_x + render_settings.SOLAR_SYSTEM_FATNESS
            zmax: float = scale.render_half_height - (pdt.moved_maxz - scale.universe_center_z) * scale.scale_z - render_settings.SOLAR_SYSTEM_FATNESS
            img_draw.rectangle((xmin-2, zmin+2, xmax+2, zmax-2), fill=None, outline='#7D0552' if not pdt.freezed else '#550A35', width=1)
            # зелёный - ИСХОДНОЕ положение ГРУППЫ регионов до масштабирований и перемещений
            xmin: float = scale.render_center_width + (pdt.left_x - scale.universe_center_x) * scale.scale_x - render_settings.SOLAR_SYSTEM_FATNESS
            zmin: float = scale.render_half_height - (pdt.top_z - scale.universe_center_z) * scale.scale_z + render_settings.SOLAR_SYSTEM_FATNESS
            xmax: float = scale.render_center_width + (pdt.right_x - scale.universe_center_x) * scale.scale_x + render_settings.SOLAR_SYSTEM_FATNESS
            zmax: float = scale.render_half_height - (pdt.bottom_z - scale.universe_center_z) * scale.scale_z - render_settings.SOLAR_SYSTEM_FATNESS
            # img_draw.rectangle((xmin-1, zmin+1, xmax+1, zmax-1), fill=None, outline='#66FF00' if not pdt.prolongated and not pdt.freezed else '#046307', width=1)
            img_draw.line((xmin-1, zmin+1, xmax+1, zmin+1), fill='#66FF00' if pdt.locked_minz <= render_settings.MOVEMENT_FREEZE_DURATION else '#046307', width=1)
            img_draw.line((xmax+1, zmin+1, xmax+1, zmax-1), fill='#66FF00' if pdt.locked_maxx <= render_settings.MOVEMENT_FREEZE_DURATION else '#046307', width=1)
            img_draw.line((xmax+1, zmax-1, xmin-1, zmax-1), fill='#66FF00' if pdt.locked_maxz <= render_settings.MOVEMENT_FREEZE_DURATION else '#046307', width=1)
            img_draw.line((xmin-1, zmax-1, xmin-1, zmin+1), fill='#66FF00' if pdt.locked_minx <= render_settings.MOVEMENT_FREEZE_DURATION else '#046307', width=1)
        # поиск ранее добавленной даты в magnifier-список
        mdt = next((m for m in self.magnifier if m[0] == render_date), None)
        if mdt is not None:
            # рыжий - АКТИВНЫЙ регион ПРЯМО СЕЙЧАС
            contour_min: (float, float, float) = mdt[1]['min']
            contour_max: (float, float, float) = mdt[1]['max']
            xmin: float = scale.render_center_width + (contour_min['x'] - scale.universe_center_x) * scale.scale_x - render_settings.SOLAR_SYSTEM_FATNESS
            zmin: float = scale.render_half_height - (contour_min['z'] - scale.universe_center_z) * scale.scale_z + render_settings.SOLAR_SYSTEM_FATNESS
            xmax: float = scale.render_center_width + (contour_max['x'] - scale.universe_center_x) * scale.scale_x + render_settings.SOLAR_SYSTEM_FATNESS
            zmax: float = scale.render_half_height - (contour_max['z'] - scale.universe_center_z) * scale.scale_z - render_settings.SOLAR_SYSTEM_FATNESS
            img_draw.rectangle((xmin, zmin, xmax, zmax), fill=None, outline='#CD7F32', width=1)

    def mark_last_time_usage(self, solar_system_id: int, curr_date: datetime.date) -> typing.Optional[int]:
        res: typing.Optional[int] = None
        for r in self.regions.values():
            if solar_system_id in r['systems']:
                region_id: int = r['id']
                if self.using.get(region_id) is None:
                    res = region_id
                self.using[region_id] = curr_date
                break
        return res

    def pass_to_date(self, curr_date: datetime.date):
        regions_to_delete: typing.Set[int] = set()
        for (region_id, dt) in self.using.items():
            if (dt + datetime.timedelta(days=render_settings.DURATION_REGION_NAME)) < curr_date:
                regions_to_delete.add(region_id)
        for region_id in regions_to_delete:
            del self.using[region_id]

    def apply_patch(self, patch: typing.Dict[str, typing.Any]):
        for (region_id, patched) in patch.items():
            r = self.regions.get(region_id)
            if r is None:
                self.regions[region_id] = patched
            else:
                r.update(patched)

    def build_magnifying_regions_by_dates(
            self,
            sde_regions,
            sde_pochven, pochven_date: datetime.datetime,
            killmails_with_dates: typing.List[typing.Any],
            industry_with_dates: typing.List[typing.Any],
            market_with_dates: typing.List[typing.Any]):
        # временные переменные
        last_date = None
        last_solar_system_id = None
        some_activity_before_patch: bool = False
        some_activity_after_patch: bool = False
        # строим список дат с которыми будут связаны min/max координаты видимых областей
        self.magnifier.clear()
        # перебираем загруженные наборы данных
        for items in (killmails_with_dates, industry_with_dates, market_with_dates):
            # пользуемся тем, что в разных сипсках содержатся объекты с одинаковыми атрибутами date и system
            for item in items:
                # стараемся не повторять одни и те же действия, если не поменялись индексы для поиска
                if last_date == item.date and last_solar_system_id == item.system:
                    continue
                if item.date < pochven_date:
                    some_activity_before_patch = True
                else:
                    some_activity_after_patch = True
                # поиск ранее добавленной даты в magnifier-список
                mdt = next((m for m in self.magnifier if m[0] == item.date), None)
                # проверка, что мы знаем идентификатор солнечной системы
                if item.system is None:
                    continue
                # проверка, что мы знает регион в котором находится эта солнечная система
                region = None
                # сначала ищев в пропатченых данных (регион Pochven и изменённые им другие регионы)
                if item.date >= pochven_date:
                    for r in sde_pochven.values():
                        if item.system in r['systems']:
                            region = r
                            break
                # если солнечная система в пропатченных данных не была найдена, то ищем в базовом наборе
                # исходим из того, что данные регионов патчем только МЕНЯЮТСЯ, но не удаляются и не добавляются)
                if region is None:
                    for r in sde_regions.values():
                        if item.system in r['systems']:
                            region = r
                            break
                if region is None:
                    continue
                # добавляем (или обновляем) координаты в magnifier-списке
                if mdt is None:
                    self.magnifier.append((item.date, {'min': region['min'], 'max': region['max']}))
                else:
                    mdt[1]['min'] = eve_sde_tools.get_min_coordinates(mdt[1]['min'], region['min'])
                    mdt[1]['max'] = eve_sde_tools.get_max_coordinates(mdt[1]['max'], region['max'])
                # запоминаем идентификаторы, по которым вёлся поиск, чтобы не гонять его вхолостую
                last_date = item.date
                last_solar_system_id = item.system
        # по умолчанию добавляем в magnifier-набор данных координаты Pochven на дату релиза
        if some_activity_before_patch and some_activity_after_patch:
            mdt = next((m for m in self.magnifier if m[0] == pochven_date), None)
            region = sde_pochven[str(10000070)]
            # добавляем (или обновляем) координаты в magnifier-списке
            if mdt is None:
                self.magnifier.append((pochven_date, {'min': region['min'], 'max': region['max']}))
            else:
                mdt[1]['min'] = eve_sde_tools.get_min_coordinates(mdt[1]['min'], region['min'])
                mdt[1]['max'] = eve_sde_tools.get_max_coordinates(mdt[1]['max'], region['max'])
        # сортируем полученный magnifier-список в порядке возрастания дат
        self.magnifier.sort(key=lambda mdt: mdt[0])

    def plan_rough_positioning(self, start_date: datetime.datetime):
        # magnifier - в этом списке точные рамки регионов и прореженные (с разрывами) даты
        # rough_positions - в этом списке рамки регионов продлены (freezed) на 15-сек интервалы, даты тоже прорежены
        self.rough_positions.clear()
        if not self.magnifier:
            return
        # получаем даты начала и конца
        curr_region = self.magnifier[0]
        curr_date: datetime.date = curr_region[0]
        till_date: datetime.date = self.magnifier[-1][0]
        # добавляем первый элемент в список "грубого позиционирования"
        prev_movement: typing.Optional[PlannedMapMovement] = PlannedMapMovement(
            curr_date,
            curr_region[1]['min']['x'], 1,
            curr_region[1]['min']['z'], 1,
            curr_region[1]['max']['x'], 1,
            curr_region[1]['max']['z'], 1)
        self.rough_positions.append(prev_movement)
        # сохраняем позиции регионов с тем чтобы была возможность вернуться к ним
        """
        deferred_positions = []
        for i in range(render_settings.MOVEMENT_FREEZE_DURATION):
            deferred_positions.append(curr_region[1])
        """
        # в начало списка копируем регион с которого magnifier-список не начинался
        if start_date < curr_date:
            self.rough_positions.insert(0, prev_movement.prolongate(start_date))
        # в цикле повторяем до последней даты
        curr_index: int = 1
        till_index: int = len(self.magnifier) - 1
        freeze_index: int = render_settings.MOVEMENT_FREEZE_DURATION
        while curr_date <= till_date:
            curr_date += datetime.timedelta(days=1)
            """
            "# список задержанных позиций периодически чистим от устаревшей инфы
            if deferred_positions:
                del deferred_positions[0]
            """
            # 1. проверям что magnifier-список не кончился
            # 2. если magnifier-список уже кончился, то план перемещений больше не плодим (freeze встаёт)
            if curr_index != till_index:
                # у текущего magnifier-элемента смотрим дату, если уже наступила, то обрабатываем элемент и идём далее
                curr_region = self.magnifier[curr_index]
                if curr_date == curr_region[0]:
                    if not prev_movement:
                        """
                        for i in range(render_settings.MOVEMENT_FREEZE_DURATION):
                            deferred_positions.append(curr_region[1])
                        """
                        prev_movement = PlannedMapMovement(
                            curr_date,
                            curr_region[1]['min']['x'], 1,
                            curr_region[1]['min']['z'], 1,
                            curr_region[1]['max']['x'], 1,
                            curr_region[1]['max']['z'], 1)
                    else:
                        ltx, ltz, rbx, rbz = (prev_movement.left_x, prev_movement.top_z, prev_movement.right_x, prev_movement.bottom_z)
                        lltx, lltz, lrbx, lrbz = (prev_movement.locked_minx + 1, prev_movement.locked_minz + 1, prev_movement.locked_maxx + 1, prev_movement.locked_maxz + 1)
                        if curr_region[1]['min']['x'] < ltx:
                            ltx = curr_region[1]['min']['x']
                            lltx = 1
                        if curr_region[1]['min']['z'] < ltz:
                            ltz = curr_region[1]['min']['z']
                            lltz = 1
                        if curr_region[1]['max']['x'] > rbx:
                            rbx = curr_region[1]['max']['x']
                            lrbx = 1
                        if curr_region[1]['max']['z'] > rbz:
                            rbz = curr_region[1]['max']['z']
                            lrbz = 1
                        """
                        ltx, ltz, rbx, rbz = (curr_region[1]['min']['x'], curr_region[1]['min']['z'], curr_region[1]['max']['x'], curr_region[1]['max']['z'])
                        lltx, lltz, lrbx, lrbz = (prev_movement.locked_minx + 1, prev_movement.locked_minz + 1, prev_movement.locked_maxx + 1, prev_movement.locked_maxz + 1)
                        deferred_positions.append(curr_region[1])
                        for d in deferred_positions:
                            if ltx < d['min']['x']:
                                ltx = d['min']['x']
                                lltx = 1
                            if ltz < d['min']['z']:
                                ltz = d['min']['z']
                                lltz = 1
                            if rbx > d['max']['x']:
                                rbx = d['max']['x']
                                lrbx = 1
                            if rbz > d['max']['z']:
                                rbz = d['max']['z']
                                lrbz = 1
                        """
                        prev_movement = PlannedMapMovement(curr_date, ltx, lltx, ltz, lltz, rbx, lrbx, rbz, lrbz)
                    self.rough_positions.append(prev_movement)
                    curr_index += 1
                    freeze_index = render_settings.MOVEMENT_FREEZE_DURATION
                # если дата не наступила, то удержимаем план перемещений в freezing-режиме
                elif curr_date < curr_region[0]:
                    if freeze_index != 1:
                        """
                        deferred_positions.append(deferred_positions[-1])
                        """
                        prev_movement = prev_movement.prolongate(curr_date)
                        self.rough_positions.append(prev_movement)
                        freeze_index -= 1
                    else:
                        """
                        deferred_positions.clear()
                        """
                        prev_movement = None
                # то чего не может быть - даты в magnifier-списке должны быть отсортированы
                else:
                    raise Exception('Illegal date sequence')
        # теперь добавляем в список недостающие фреймы (рамки регионов)
        prev_position: PlannedMapMovement = self.rough_positions[0]
        curr_date: datetime.date = prev_position.date
        curr_index: int = 1
        while curr_date < till_date:
            curr_date += datetime.timedelta(days=1)
            if curr_index < len(self.rough_positions):
                curr_position: PlannedMapMovement = self.rough_positions[curr_index]
                if curr_date == curr_position.date:
                    prev_position = curr_position
                    curr_index += 1
                    continue
            prev_position = prev_position.prolongate(curr_date)
            self.rough_positions.insert(curr_index, prev_position)
            curr_index += 1

    def plan_precise_positioning(self, render_scale: RenderScale):
        # определяем массивы где будем хранить индексы тех рамок в отношении которых уже выполнялось расширение,
        # увеличивать значения можно, уменьшать или повторять нельзя (предохранение от многократного расширения туда же)
        grows_minx, grows_minz, grows_maxx, grows_maxz = ([], [], [], [])
        shrinks_minx, shrinks_minz, shrinks_maxx, shrinks_maxz = ([], [], [], [])
        for l in (grows_minx, grows_minz, grows_maxx, grows_maxz, shrinks_minx, shrinks_minz, shrinks_maxx, shrinks_maxz):
            for idx in range(len(self.rough_positions)):
                l.append(idx)
        # перебираем рамки регионов и увеличиваем их если необходимо
        last_index: int = len(self.rough_positions) - 1
        for (curr_index, curr_p) in enumerate(self.rough_positions):
            # определяем изменение габаритных размеров рамок групп регионов (на несколько суток вперёд)
            grow_minx, grow_minz, grow_maxx, grow_maxz = (curr_p.moved_minx, curr_p.moved_minz, curr_p.moved_maxx, curr_p.moved_maxz)
            shrink_minx, shrink_minz, shrink_maxx, shrink_maxz = (curr_p.moved_minx, curr_p.moved_minz, curr_p.moved_maxx, curr_p.moved_maxz)
            # определяем кол-во дней за которое необходимо увеличить соответствующую границу?
            grow_need_minx, grow_need_minz, grow_need_maxx, grow_need_maxz = (0, 0, 0, 0)
            shrink_need_minx, shrink_need_minz, shrink_need_maxx, shrink_need_maxz = (0, 0, 0, 0)
            for next_index in range(curr_index + 1, curr_index + 10):
                if next_index >= last_index:
                    break
                next_p: PlannedMapMovement = self.rough_positions[next_index]
                need_step: int = next_index - curr_index
                # ---
                if (grow_need_minx == 0) and (next_p.left_x < grow_minx):
                    grow_minx = next_p.left_x
                    grow_need_minx = need_step
                if shrink_need_minx == 0:
                    if grows_minx[next_index] != next_index:
                        shrink_minx = None
                    elif shrink_minx and (next_p.left_x > shrink_minx):
                        shrink_minx = next_p.left_x
                        shrink_need_minx = need_step
                # ---
                if (grow_need_minz == 0) and (next_p.top_z < grow_minz):
                    grow_minz = next_p.top_z
                    grow_need_minz = need_step
                if shrink_need_minz == 0:
                    if grows_minz[next_index] != next_index:
                        shrink_minz = None
                    elif shrink_minz and (next_p.top_z > shrink_minz):
                        shrink_minz = next_p.top_z
                        shrink_need_minz = need_step
                # ---
                if (grow_need_maxx == 0) and (next_p.right_x > grow_maxx):
                    grow_maxx = next_p.right_x
                    grow_need_maxx = need_step
                if shrink_need_maxx == 0:
                    if grows_maxx[next_index] != next_index:
                        shrink_maxx = None
                    elif shrink_maxx and (next_p.right_x < shrink_maxx):
                        shrink_maxx = next_p.right_x
                        shrink_need_maxx = need_step
                # ---
                if (grow_need_maxz == 0) and (next_p.bottom_z > grow_maxz):
                    grow_maxz = next_p.bottom_z
                    grow_need_maxz = need_step
                if shrink_need_maxz == 0:
                    if grows_maxz[next_index] != next_index:
                        shrink_maxz = None
                    elif shrink_maxz and (next_p.bottom_z < shrink_maxz):
                        shrink_maxz = next_p.bottom_z
                        shrink_need_maxz = need_step
            # определяем направление движения рамок групп регионов (интерпретируется как "граница двигается в сторону")
            grow_move_minx, grow_move_minz, grow_move_maxx, grow_move_maxz = (
                grow_minx - curr_p.moved_minx,
                grow_minz - curr_p.moved_minz,
                grow_maxx - curr_p.moved_maxx,
                grow_maxz - curr_p.moved_maxz)
            shrink_move_minx, shrink_move_minz, shrink_move_maxx, shrink_move_maxz = (
                shrink_minx - curr_p.moved_minx if shrink_minx else 0.0,
                shrink_minz - curr_p.moved_minz if shrink_minz else 0.0,
                shrink_maxx - curr_p.moved_maxx if shrink_maxx else 0.0,
                shrink_maxz - curr_p.moved_maxz if shrink_maxz else 0.0)
            # увеличивать габариты рамки можно всегда, т.к. в неё попадут все нужные регионы
            if grow_move_minx < -1.0:
                delta: float = grow_move_minx / grow_need_minx
                need_index: int = curr_index + grow_need_minx
                for idx in range(curr_index + 1, need_index):
                    if grows_minx[idx] < need_index:
                        self.rough_positions[idx].moved_minx = curr_p.moved_minx + delta * (idx - curr_index)
                        grows_minx[idx] = need_index
            elif shrink_move_minx > 1.0:
                delta: float = shrink_move_minx / shrink_need_minx
                need_index: int = curr_index + shrink_need_minx
                for idx in range(curr_index + 1, need_index):
                    if grows_minx[idx] < need_index and shrinks_minx[idx] < need_index:
                        self.rough_positions[idx].moved_minx = curr_p.moved_minx + delta * (idx - curr_index)
                        grows_minx[idx] = need_index
                        shrinks_minx[idx] = need_index
            # ---
            if grow_move_minz < -1.0:
                delta: float = grow_move_minz / grow_need_minz
                need_index: int = curr_index + grow_need_minz
                for idx in range(curr_index + 1, need_index):
                    if grows_minz[idx] < need_index:
                        self.rough_positions[idx].moved_minz = curr_p.moved_minz + delta * (idx - curr_index)
                        grows_minz[idx] = need_index
            elif shrink_move_minz > 1.0:
                delta: float = shrink_move_minz / shrink_need_minz
                need_index: int = curr_index + shrink_need_minz
                for idx in range(curr_index + 1, need_index):
                    if grows_minz[idx] < need_index and shrinks_minz[idx] < need_index:
                        self.rough_positions[idx].moved_minz = curr_p.moved_minz + delta * (idx - curr_index)
                        grows_minz[idx] = need_index
                        shrinks_minz[idx] = need_index
            # ---
            if grow_move_maxx > 1.0:
                delta: float = grow_move_maxx / grow_need_maxx
                need_index: int = curr_index + grow_need_maxx
                for idx in range(curr_index + 1, need_index):
                    if grows_maxx[idx] < need_index:
                        self.rough_positions[idx].moved_maxx = curr_p.moved_maxx + delta * (idx - curr_index)
                        grows_maxx[idx] = need_index
            elif shrink_move_maxx < -1.0:
                delta: float = shrink_move_maxx / shrink_need_maxx
                need_index: int = curr_index + shrink_need_maxx
                for idx in range(curr_index + 1, need_index):
                    if grows_maxx[idx] < need_index and shrinks_maxx[idx] < need_index:
                        self.rough_positions[idx].moved_maxx = curr_p.moved_maxx + delta * (idx - curr_index)
                        grows_maxx[idx] = need_index
                        shrinks_maxx[idx] = need_index
            # ---
            if grow_move_maxz > 1.0:
                delta: float = grow_move_maxz / grow_need_maxz
                need_index: int = curr_index + grow_need_maxz
                for idx in range(curr_index + 1, need_index):
                    if grows_maxz[idx] < need_index:
                        self.rough_positions[idx].moved_maxz = curr_p.moved_maxz + delta * (idx - curr_index)
                        grows_maxz[idx] = need_index
            elif shrink_move_maxz < -1.0:
                delta: float = shrink_move_maxz / shrink_need_maxz
                need_index: int = curr_index + shrink_need_maxz
                for idx in range(curr_index + 1, need_index):
                    if grows_maxz[idx] < need_index and shrinks_maxz[idx] < need_index:
                        self.rough_positions[idx].moved_maxz = curr_p.moved_maxz + delta * (idx - curr_index)
                        grows_maxz[idx] = need_index
                        shrinks_maxz[idx] = need_index
        # завершаем коррекцию рамок регионов сохраняя пропорции видимой области карты (выравниваем рамки по
        # ширине и по высоте, не допускаем их выход за пределы видимой области экрана при изменении пропорций)
        for p in self.rough_positions:
            p.do_precise_calculation(render_scale)


class ImportedData:
    def __init__(self):
        pass


def read_csv_file(
        fname: str,
        file_date_col: int,
        start_date: typing.Optional[datetime.datetime],
        stop_date: typing.Optional[datetime.datetime],
        attributes: typing.List[typing.Tuple[str, typing.Type]],
        preload_early_dates: bool = False) -> typing.List[typing.Any]:
    list_with_dates: typing.List[ImportedData] = []
    with open(fname, newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[file_date_col], '%Y-%m-%d')
            if preload_early_dates:
                if stop_date and stop_date < dt:
                    continue
            else:
                if start_date:
                    if stop_date:
                        if dt < start_date or stop_date < dt:
                            continue
                    elif dt < start_date:
                        continue
                elif stop_date and stop_date < dt:
                    continue
            # добавление объекта в список в том виде в котором задан формат файла
            data: ImportedData = ImportedData()
            for (idx, a) in enumerate(attributes):
                val: str = row[idx]
                if a[1] == int:
                    setattr(data, a[0], int(val) if val else None)
                elif a[1] == float:
                    setattr(data, a[0], float(val) if val else None)
                elif a[1] == datetime.datetime:
                    if idx == file_date_col:
                        setattr(data, a[0], dt)
                    else:
                        setattr(data, a[0], datetime.datetime.strptime(val, '%Y-%m-%d') if val else None)
                else:
                    setattr(data, a[0], val)
            list_with_dates.append(data)
        del reader
    return list_with_dates


def render_base_image(cwd: str, input_dir: str, out_dir: str, date_from: str, date_to: str, verbose: bool = False):
    sde_names = eve_sde_tools.read_converted(cwd, "invNames")
    if verbose:
        print("Read {} names in Universe".format(len(sde_names)))
    sde_positions = eve_sde_tools.read_converted(cwd, "fsdUniversePositions")
    if verbose:
        print("Read {} solar systems positions in Universe".format(len(sde_positions)))

    # подготовка координат регионов для отборажения на карте их названий и для расчёта динамического изменения карты
    sde_regions = eve_sde_tools.read_converted(cwd, "fsdRegions")
    sde_pochven = eve_sde_tools.read_converted(cwd, "fsdRegions_2020oct13_patch")
    if verbose:
        print("Read {} regions and their positions plus {} patch for dates after 2020 October 13".format(len(sde_regions), len(sde_pochven)))
    # переконвертируем строки в числа и список делаем set-ом
    for r in sde_regions.values():
        systems_as_int: typing.Set[int] = set()
        for s in r['systems']:
            systems_as_int.add(int(s))
        r['systems'] = systems_as_int
    for r in sde_pochven.values():
        systems_as_int: typing.Set[int] = set()
        for s in r['systems']:
            systems_as_int.add(int(s))
        r['systems'] = systems_as_int

    # рассчитываем пропорции и региона на изображении, которые будут использоваться для отрисовки разной информации
    render_scale = RenderScale()
    render_scale.calc(sde_positions)
    render_scale.choose_font_size()
    if verbose:
        print("Min and max positions:", render_scale.min_x, render_scale.max_x, render_scale.min_z, render_scale.max_z)
        print("Center positions:", render_scale.universe_center_x, render_scale.universe_center_z)
        print("Min and max luminosity:", render_scale.min_luminosity, render_scale.max_luminosity)
        print('Scale {} {} for {}x{} bitmap'.format(render_scale.scale_x, render_scale.scale_z, render_settings.RENDER_WIDTH, render_settings.RENDER_HEIGHT))
        print('Rectangle of universe in bitmap {} x {} : {} x {}'.format(
            render_scale.render_center_width + (render_scale.min_x-render_scale.universe_center_x)*render_scale.scale_x,
            render_scale.render_half_height - (render_scale.min_z-render_scale.universe_center_z)*render_scale.scale_z,
            render_scale.render_center_width + (render_scale.max_x-render_scale.universe_center_x)*render_scale.scale_x,
            render_scale.render_half_height - (render_scale.max_z-render_scale.universe_center_z)*render_scale.scale_z))
        print('Scale {} of luminosity for min {} and max {}'.format(
            render_scale.scale_luminosity,
            render_settings.LUMINOSITY_MIN_BOUND+render_scale.min_luminosity*render_scale.scale_luminosity,
            render_settings.LUMINOSITY_MIN_BOUND+(render_scale.max_luminosity-render_scale.min_luminosity)*render_scale.scale_luminosity))
    # настраиваем шрифты, которым будем рисовать события даты и т.п.
    events_font = ImageFont.truetype("arial.ttf", render_scale.fontsize)
    date_font = ImageFont.truetype("arial.ttf", render_scale.calc_font_size(50))
    region_font = ImageFont.truetype("arial.ttf", render_scale.calc_font_size(55))
    # выбор дат для отрисовки сцен
    start_date = datetime.datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
    stop_date = datetime.datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
    pochven_date = datetime.datetime.strptime('2020-10-13', '%Y-%m-%d')

    # читаем данные из файлов
    events_with_dates = read_csv_file(
        '{}/{}'.format(input_dir, render_settings.FILE_EVENTS_NAME), render_settings.FILE_EVENTS_COL_DATE,
        start_date, stop_date,
        render_settings.FILE_EVENTS_COLS)
    killmails_with_dates = read_csv_file(
        '{}/{}'.format(input_dir, render_settings.FILE_KILLMAILS_NAME), render_settings.FILE_KILLMAILS_COL_DATE,
        start_date, stop_date,
        render_settings.FILE_KILLMAILS_COLS)
    industry_with_dates = read_csv_file(
        '{}/{}'.format(input_dir, render_settings.FILE_INDUSTRY_NAME), render_settings.FILE_INDUSTRY_COL_DATE,
        start_date, stop_date,
        render_settings.FILE_INDUSTRY_COLS)
    market_with_dates = read_csv_file(
        '{}/{}'.format(input_dir, render_settings.FILE_MARKET_NAME), render_settings.FILE_MARKET_COL_DATE,
        start_date, stop_date,
        render_settings.FILE_MARKET_COLS)
    employment_with_dates = read_csv_file(
        '{}/{}'.format(input_dir, render_settings.FILE_EMPLOYMENT_NAME), render_settings.FILE_EMPLOYMENT_COL_ENTER_DATE,
        start_date, stop_date,
        render_settings.FILE_EMPLOYMENT_COLS,
        preload_early_dates=True)

    # определяем начало диапазона, который будет участвовать в создании кадров
    if start_date:
        render_date = start_date
    else:
        dts: typing.List[str] = []
        if events_with_dates:
            dts.append(events_with_dates[0].date)
        if killmails_with_dates:
            dts.append(killmails_with_dates[0].date)
        if industry_with_dates:
            dts.append(industry_with_dates[0].date)
        if market_with_dates:
            dts.append(market_with_dates[0].date)
        render_date = None
        for dt in dts:
            if render_date is None or render_date > dt:
                render_date = dt
    # определяем конец диапазона, который будет участвовать в создании кадров
    if not stop_date:
        dtf: typing.List[str] = []
        if events_with_dates:
            dtf.append(events_with_dates[-1].date)
        if killmails_with_dates:
            dtf.append(killmails_with_dates[-1].date)
        if industry_with_dates:
            dtf.append(industry_with_dates[-1].date)
        if market_with_dates:
            dtf.append(market_with_dates[-1].date)
        stop_date = None
        for dt in dtf:
            if stop_date is None or stop_date < dt:
                stop_date = dt
    # вывод отладочной информации, если требуется
    if verbose:
        print('Loaded {} events, {} killmails, {} jobs, {} markets'.format(
            len(events_with_dates),
            len(killmails_with_dates),
            len(industry_with_dates),
            len(market_with_dates)
        ))
        print('Date from {} and date to {} choosen'.format(render_date, stop_date))

    # включение/отключение режима динамического изменения карты (масштаб, перемещение фокуса и т.п.)
    regions_activity = RenderRegionsActivity(sde_regions)
    if render_settings.MOVEMENT_MAP_ENABLED:
        # расчёт движения карты, т.н. "режим лупы" (строится ДО накладывания pochven-исправления)
        regions_activity.build_magnifying_regions_by_dates(
            sde_regions,
            sde_pochven, pochven_date,
            killmails_with_dates,
            industry_with_dates,
            market_with_dates)
        regions_activity.plan_rough_positioning(render_date)
        regions_activity.plan_precise_positioning(render_scale)
        # если начало работы программы задано после появления Pochven в игре, то тихо корректируем регионы без
        # изменения изображений на карте
        if render_date > pochven_date:
            regions_activity.apply_patch(sde_pochven)
            if verbose:
                print('Pochven'' patch applied to stored regions, {} regions corrected'.format(len(sde_pochven)))
            del sde_pochven
            sde_pochven = None
    # уничтожаем исходную информацию о регионах, пользоваться нельзя - она уже пропатчена (возможно?)
    del sde_regions

    # набор данных, которые подвергаются мерцанию и переменные для статистики
    render_fade_in: RenderFadeInRepository = RenderFadeInRepository()
    maximum_num_of_industry_jobs = 0
    maximum_isk_per_day = 0
    # сортируем список звёздных систем в порядке возрастания составляющей y, так чтобы при рисовании их на плоскости
    # верхние были над нижними
    sorted_solar_systems: typing.List[typing.Any] = list(sde_positions.values())
    sorted_solar_systems.sort(key=lambda ss: ss[1], reverse=False)

    # выбор размер пиктограммы пилота (в коллекции находятся размеры от 32px до 22px,
    # где 34px соответствует высоте шрифта size=46)
    pilot_img_height: int = int(render_scale.fontsize / 1.3)
    if pilot_img_height >= 36:
        pilot_img_height = 36
    elif pilot_img_height <= 22:
        pilot_img_height = 14
    elif 1 == (pilot_img_height % 2):
        pilot_img_height -= 1
    # загрузка png изображений для отрисовки пиктограмм на карте
    pilot_img = Image.open("{}/images/pilot/fill_{}.png".format(cwd, pilot_img_height))
    pilot_contour_img = Image.open("{}/images/pilot/contour_{}.png".format(cwd, pilot_img_height))
    # конструируем коллекцию пилотов (членов корпораций)
    pilots: RenderPilots = RenderPilots(employment_with_dates, pilot_img, pilot_contour_img)
    del employment_with_dates

    # номер фрейма, который задаёт имя файла и последовательно используется ffmpeg-программой
    image_index: int = 0
    while True:
        num_new_events: int = 0
        # получаем дату "сегодняшнего дня"
        render_date_str: str = datetime.datetime.strftime(render_date, '%Y-%m-%d')
        if verbose:
            print('==', render_date_str)
        # добавляем информацию о появлении нового региона Pochven в EVE Online
        if sde_pochven is not None and (render_date == pochven_date):
            regions_activity.apply_patch(sde_pochven)
            if verbose:
                print(' pochven'' patch applied to stored regions, {} regions corrected'.format(len(sde_pochven)))
            del sde_pochven
            sde_pochven = None
            # ---
            render_fade_in.add_region(RenderFadeInRegion(10000070, color=render_settings.EVENTS_SETUP[5][0]))  # region_id=Pochven
            render_fade_in.add_event(RenderFadeInEvent("Pochven is the region of space introduces at October 13 2020", 5))
            num_new_events += 1
        # добавляем события "сегодняшнего дня" в список отрисовки
        if events_with_dates:
            while render_date == events_with_dates[0].date:
                e: RenderFadeInEvent = RenderFadeInEvent(
                    events_with_dates[0].txt,
                    events_with_dates[0].level)
                render_fade_in.add_event(e)
                num_new_events += 1
                del events_with_dates[0]
                if not events_with_dates:
                    break
        # добавляем киллмылы "сегодняшнего для" в список отрисовки, готовим маркеры для карты
        if killmails_with_dates:
            num_new_killmails: int = 0
            while render_date == killmails_with_dates[0].date:
                solar_system_id: int = killmails_with_dates[0].system
                new_region_id = regions_activity.mark_last_time_usage(solar_system_id, render_date)
                if new_region_id is not None:
                    render_fade_in.add_region(RenderFadeInRegion(new_region_id))
                # ---
                p = sde_positions.get(str(solar_system_id))
                k: RenderFadeInKillmail = RenderFadeInKillmail(
                    killmails_with_dates[0].victim == 1,
                    killmails_with_dates[0].txt,
                    killmails_with_dates[0].shiptype,
                    killmails_with_dates[0].mass,
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_killmail(k)
                num_new_killmails += 1
                del killmails_with_dates[0]
                if not killmails_with_dates:
                    break
            if verbose and num_new_killmails:
                print(' {} new killmails'.format(num_new_killmails))
        # добавляем статистику производства "сегодняшнего для" в список отрисовки, готовим маркеры для карты
        if industry_with_dates:
            num_new_industry_jobs: int = 0
            while render_date == industry_with_dates[0].date:
                solar_system_id: typing.Optional[int] = industry_with_dates[0].system
                p = None
                if solar_system_id is not None:
                    new_region_id = regions_activity.mark_last_time_usage(solar_system_id, render_date)
                    if new_region_id is not None:
                        render_fade_in.add_region(RenderFadeInRegion(new_region_id))
                    p = sde_positions.get(str(solar_system_id))
                k: RenderFadeInIndustry = RenderFadeInIndustry(
                    industry_with_dates[0].jobs,
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_industry(k)
                num_new_industry_jobs += industry_with_dates[0].jobs
                del industry_with_dates[0]
                if not industry_with_dates:
                    break
            if verbose and num_new_industry_jobs:
                print(' {} new industry stat'.format(num_new_industry_jobs))
            if num_new_industry_jobs > maximum_num_of_industry_jobs:
                maximum_num_of_industry_jobs = num_new_industry_jobs
                e: RenderFadeInEvent = RenderFadeInEvent('Industry achievement , {} jobs'.format(maximum_num_of_industry_jobs), 3)
                render_fade_in.add_event(e)
                num_new_events += 1
        # добавляем статистику маркета "сегодняшнего для" в список отрисовки, готовим маркеры для карты
        if market_with_dates:
            sum_isk_per_day: int = 0
            while render_date == market_with_dates[0].date:
                solar_system_id: typing.Optional[int] = market_with_dates[0].system
                p = None
                if solar_system_id is not None:
                    new_region_id = regions_activity.mark_last_time_usage(solar_system_id, render_date)
                    if new_region_id is not None:
                        render_fade_in.add_region(RenderFadeInRegion(new_region_id))
                    p = sde_positions.get(str(solar_system_id))
                k: RenderFadeInMarket = RenderFadeInMarket(
                    market_with_dates[0].isk,
                    p[0] if p is not None else None, p[2] if p is not None else None)
                render_fade_in.add_market(k)
                sum_isk_per_day += int(market_with_dates[0].isk)
                del market_with_dates[0]
                if not market_with_dates:
                    break
            if verbose and sum_isk_per_day:
                print(' {} ISK in market operations'.format(sum_isk_per_day))
            if sum_isk_per_day > maximum_isk_per_day:
                maximum_isk_per_day = sum_isk_per_day
                e: RenderFadeInEvent = RenderFadeInEvent('Market achievement, {:,d} ISK'.format(maximum_isk_per_day), 4)
                render_fade_in.add_event(e)
                num_new_events += 1
        # выводим отладку на экран, если включена
        if verbose and num_new_events:
            print(' {} new events'.format(num_new_events))

        # ---
        for frame_idx in range(render_settings.DURATION_DATE):
            # создаём канву на которой будем рисовать
            canvas = Image.new('RGB', (render_settings.RENDER_WIDTH, render_settings.RENDER_HEIGHT), 'black')
            img_draw = ImageDraw.Draw(canvas, 'RGB')
            # наносим на изображение контуры регионов (отладочный режим, рамки регионов рисуются под картой)
            if render_settings.MOVEMENT_MAP_ENABLED and render_settings.MOVEMENT_MAP_DEBUG:
                regions_activity.draw_contours_of_magnifier_debug_only(img_draw, render_scale, render_date)
                regions_activity.draw_contours_of_regions_debug_only(img_draw, render_scale, region_font)
            # генерируем рисовалку вселенной и корпоративных событий
            renderer: RenderUniverse = RenderUniverse(canvas, img_draw, render_scale, date_font, events_font, events_font, region_font)
            # наносим на изображение список пилотов
            renderer.draw_pilots(pilots, render_date, frame_idx / render_settings.DURATION_DATE)
            # рисуем названия регионов на карте
            renderer.draw_regions(regions_activity.regions, render_fade_in.regions)
            # генерируем базовый фон с нанесёнными на него звёздами Вселенной EVE
            for p in sorted_solar_systems:
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
            # DEBUG: canvas.show()
            # DEBUG: return

        del img_draw
        del canvas
        # ---
        if render_date == stop_date:
            break
        regions_activity.pass_to_date(render_date)
        render_date += datetime.timedelta(days=1)

    del sde_positions
    del sde_names
