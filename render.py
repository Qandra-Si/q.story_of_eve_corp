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
RENDER_FRAME_RATE: int = 5  # 24
SOLAR_SYSTEM_FATNESS: float = 2.0
LUMINOSITY_MIN_BOUND: int = 100  # 50 хорошо видно в тёмное время суток на тёмном экране, 100 видно днём
LUMINOSITY_MAX_BOUND: int = 255
NUMBER_OF_EVENTS: int = 50
NUMBER_OF_KILLMAILS_IN_LIST: int = 30  # шрифт используется такой же, регион для killmails занимает меньше места
KILLMAIL_MAP_MIN_TRANSPARENT: float = 0.1  # 0 максимальный уровень непрозрачности
KILLMAIL_MAP_MAX_TRANSPARENT: float = 0.9  # 255 максимальный уровень прозрачности
KILLMAIL_MIN_FATNESS: float = SOLAR_SYSTEM_FATNESS * 4  # маркер гибели корабля больше солнечной системы, далее по массе
# интервалы времени (д.б. согласованы с RENDER_FRAME_RATE)
DURATION_DATE_SEC: int = 2  # одна дата рисуется 2 секунды
DURATION_DATE: int = RENDER_FRAME_RATE * DURATION_DATE_SEC  # одна дата рисуется 2*24 фрейма, т.е. 2 секунды
# цвета, выбираем тут https://www.computerhope.com/htmcolor.htm
EVENTS_SETUP: ((int, int, int), int) = [
    # color              duration sec
    ((0xff, 0xe5, 0xb4), 8),  # peach (персиковый) warning "Hello, Qandra Si", живёт на экране 8 секунд
    ((0xb6, 0xb6, 0xb4), 4),  # gray cloud (светло серый) notice "Qandra Si has come", живёт на экране 4 секунды
    ((0x79, 0x79, 0x79), 4),  # platinum gray (сероватый) notice "Qandra Si gone", живёт на экране 4 секунды
]
KILLMAILS_SETUP: (int, int, int) = [
    # color              duration sec
    ((0xdc, 0x38, 0x1f), DURATION_DATE_SEC),      # (в списке событий killmail не упоминается), живёт на экране одни сутки
    ((0xdc, 0x38, 0x1f), DURATION_DATE_SEC * 2),  # grapefruit (красный) warning "Zorky Graf Tumidus lost Rhea", живёт на экране 2 суток
]

# формат csv файла events-utf8.txt
FILE_EVENTS_NAME: str = "events-utf8.txt"
FILE_EVENTS_COL_DATE: int = 0
FILE_EVENTS_COL_LEVEL: int = 1
FILE_EVENTS_COL_TXT: int = 2
# формат csv файла killmails-utf8.txt
FILE_KILLMAILS_NAME: str = "killmails-utf8.txt"
FILE_KILLMAILS_COL_DATE: int = 0
FILE_KILLMAILS_COL_PILOT: int = 1
FILE_KILLMAILS_COL_SHIP: int = 2
FILE_KILLMAILS_COL_SHIPTYPE: int = 3
FILE_KILLMAILS_COL_MASS: int = 4
FILE_KILLMAILS_COL_SYSTEM: int = 5


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

    def __init__(self, txt: str, ship_type: int, ship_mass: float, x: typing.Optional[float], z: typing.Optional[float]):
        self.__level: int = 1
        if ship_type in self.__do_not_show_in_list:
            self.__level: int = 0
        self.__color: typing.Optional[(int, int, int)] = KILLMAILS_SETUP[self.__level][0]
        self.txt: str = txt
        self.mass: float = ship_mass
        self.x: typing.Optional[float] = x
        self.z: typing.Optional[float] = z
        self.opacity: float = 1.0
        lifetime_frames: int = KILLMAILS_SETUP[self.__level][1] * RENDER_FRAME_RATE
        self.transparency_frame: float = 1.0 / lifetime_frames  # мера прозрачности, добавляемая каждый фрейм

    def pass_frame(self):
        self.opacity -= self.transparency_frame
        if self.opacity < 0.0:
            self.opacity = 0.0

    @property
    def show_in_list(self) -> bool:
        return self.__level > 0

    @property
    def show_on_map(self) -> bool:
        return self.x is not None

    @property
    def disappeared(self) -> bool:
        return self.opacity < 0.08

    @property
    def list_color(self) -> (int, int, int):
        return int(self.__color[0] * self.opacity), int(self.__color[1] * self.opacity), int(self.__color[2] * self.opacity)

    @property
    def map_color(self) -> (int, int, int):
        t: float = 1.0 - self.map_transparent
        return int(self.__color[0] * t), int(self.__color[1] * t), int(self.__color[2] * t)

    @property
    def map_transparent(self) -> float:
        return KILLMAIL_MAP_MIN_TRANSPARENT + (1.0-self.opacity) * (KILLMAIL_MAP_MAX_TRANSPARENT - KILLMAIL_MAP_MIN_TRANSPARENT)

    @property
    def map_radius(self) -> float:
        radius: float = self.mass / 50000000  # Rhea 960'000'000, Capsule 32'000, Venture 1'200'000
        if radius < KILLMAIL_MIN_FATNESS:
            radius = KILLMAIL_MIN_FATNESS
        return radius


class RenderFadeInRepository:
    def __init__(self):
        self.events: typing.List[RenderFadeInEvent] = []
        self.__killmails: typing.List[RenderFadeInKillmail] = []

    def add_event(self, item: RenderFadeInEvent):
        if len(self.events) == NUMBER_OF_EVENTS:
            del self.events[NUMBER_OF_EVENTS-1]
        self.events.insert(0, item)

    def add_killmail(self, item: RenderFadeInKillmail):
        self.__killmails.insert(0, item)
        
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


class RenderUniverse:
    def __init__(
            self,
            img_draw: ImageDraw,
            scale: RenderScale,
            date_font: ImageFont,
            events_font: ImageFont,
            killmails_font: ImageFont):
        self.img_draw = img_draw
        self.scale = scale
        self.date_font = date_font
        self.events_font = events_font
        self.killmails_font = killmails_font

    def draw_solar_system(self, x: float, z: float, luminosity: float):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        __fatness: float = SOLAR_SYSTEM_FATNESS
        __luminosity: int = int(LUMINOSITY_MIN_BOUND + (sqrt(luminosity) - self.scale.min_luminosity) * self.scale.scale_luminosity)
        __shape = [(__x - __fatness, __z - __fatness), (__x + __fatness, __z + __fatness)]
        self.img_draw.ellipse(__shape, fill=(__luminosity, __luminosity, __luminosity))

    def highlight_solar_system(self, x: float, z: float, color: (int, int, int), fatness: float):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        # DEBUG:
        print("{}x{} {} {}".format(int(__x), int(__z), color, fatness))
        shape = [(__x - fatness, __z - fatness), (__x + fatness, __z + fatness)]
        self.img_draw.ellipse(shape, fill=color)

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
            self.highlight_solar_system(k.x, k.z, k.map_color, k.map_radius)

    def draw_date_caption(self, date: str):
        __x: float = self.scale.render_center_width + (self.scale.min_x - self.scale.universe_center_x) * self.scale.scale_x
        self.img_draw.text((__x, 10), date, fill=(140, 140, 140), font=self.date_font)


def render_base_image(cwd: str, input_dir: str, out_dir: str, verbose: bool = False):
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

    """
    !!!!!!!!!!!
    """

    start_date = datetime.datetime.strptime('2019-09-25', '%Y-%m-%d')
    stop_date = datetime.datetime.strptime('2019-12-30', '%Y-%m-%d')
    start_date = datetime.datetime.strptime('2021-09-26', '%Y-%m-%d')
    stop_date = datetime.datetime.strptime('2021-09-30', '%Y-%m-%d')

    events_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_EVENTS_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_EVENTS_COL_DATE], '%Y-%m-%d')
            if start_date <= dt <= stop_date:
                events_with_dates.append(row)
    killmails_with_dates = []
    with open('{}/{}'.format(input_dir, FILE_KILLMAILS_NAME), newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            dt = datetime.datetime.strptime(row[FILE_KILLMAILS_COL_DATE], '%Y-%m-%d')
            if start_date <= dt <= stop_date:
                killmails_with_dates.append(row)
    if verbose:
        print('Loaded {} events and {} killmails'.format(len(events_with_dates), len(killmails_with_dates)))

    render_date = start_date
    render_fade_in: RenderFadeInRepository = RenderFadeInRepository()
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
                    '{} lost {}'.format(killmails_with_dates[0][FILE_KILLMAILS_COL_PILOT], killmails_with_dates[0][FILE_KILLMAILS_COL_SHIP]),
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

        # ---
        for frame_idx in range(DURATION_DATE):
            # создаём канву на которой будем рисовать
            canvas = Image.new('RGB', (RENDER_WIDTH, RENDER_HEIGHT), 'black')
            img_draw = ImageDraw.Draw(canvas, 'RGB')

            img_draw.rectangle((0, 0, 400, 400), fill='#646D7E')

            fatness: float = 17.5
            blur_size: int = 4
            border_width: int = blur_size + 3
            img_mask = Image.new("L", (2*int(fatness+0.99+border_width), 2*int(fatness+0.99+border_width)), 0)
            print(img_mask.size)
            draw_mask = ImageDraw.Draw(img_mask)
            draw_mask.ellipse((border_width, border_width, border_width+int(2*fatness), border_width+int(2*fatness)), fill=128)
            img_mask_blur = img_mask.filter(ImageFilter.GaussianBlur(blur_size))

            canvas.paste(img_mask, (50, 50), img_mask)
            canvas.paste(img_mask_blur, (50, 100), img_mask)

            red_square = Image.new('RGB', img_mask.size, 'red')
            red_square.putalpha(img_mask)
            canvas.paste(red_square, (100, 50), red_square)

            red_square = Image.new('RGB', img_mask.size, 'red')
            red_square.putalpha(img_mask_blur)
            canvas.paste(red_square, (100, 100), red_square)

            # red_square = Image.new('RGB', (100, 100), 'red')
            # red_square.putalpha(img_mask)
            # canvas.paste(red_square, (0, 0), red_square)

            #c2 = Image.new('RGBA', (100, 100), 'red')
            #canvas.paste(c2, (0, 0), c2)

            # генерируем рисовалку вселенной и корпоративных событий
            renderer: RenderUniverse = RenderUniverse(img_draw, render_scale, date_font, events_font, events_font)
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
            # событиям, находящимся в репозитории "затухания" повышается прозрачность
            render_fade_in.pass_frame()

            # получаем координаты Житы
            # p = sde_positions.get("30000142")
            # renderer.highlight_solar_system(p[0], p[2], (255, 60, 60, 50))

            canvas.save('{}/{}_{:0>3}.png'.format(out_dir, render_date_str, frame_idx))
            # canvas.show()
            return

        del img_draw
        del canvas
        # time.sleep(1)
        # ---
        if render_date == stop_date:
            break
        render_date += datetime.timedelta(days=1)

    del sde_positions
    del sde_names
