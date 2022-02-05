import eve_sde_tools
from math import sqrt
from PIL import Image, ImageDraw, ImageFont


# Смотрим рекомендуемые настройки кодирования здесь https://support.google.com/youtube/answer/1722171?hl=ru
# выбираем частоту кадров, разрешение и соотношение сторон, останавливаемся на Ultra HD 4K.
# Внимание! крайне не рекомендуется менять следующие параметры, задавая их отличными от одного из перечисленных
# по ссылке вариантов, во избежание перекодирования изображений сгенерированных этой программой. Изображения содержат
# текст, которые после переконвертации может стать плохочитаемым.
RENDER_WIDTH: int = 3840
RENDER_HEIGHT: int = 2160
RENDER_FRAME_RATE: int = 24
SOLAR_SYSTEM_FATNESS: float = 2.0
LUMINOSITY_MIN_BOUND: int = 50
LUMINOSITY_MAX_BOUND: int = 255
NUMBER_OF_EVENTS: int = 50


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
            print(font.getsize("Qandra Si"))
            self.fontsize += 1
            font = ImageFont.truetype("arial.ttf", self.fontsize)
        # опционально уменьшаем размер шрифта, чтобы была уверенность, что символы не будут наползать друг на друга
        self.fontsize -= 1
        del font


class RenderUniverse:
    def __init__(
            self,
            img_draw: ImageDraw,
            scale: RenderScale,
            events_font: ImageFont,
            date_font: ImageFont):
        self.img_draw = img_draw
        self.scale = scale
        self.events_font = events_font
        self.date_font = date_font

    def draw_solar_system(self, x: float, z: float, luminosity: float):
        __x: float = self.scale.render_center_width + (x - self.scale.universe_center_x) * self.scale.scale_x
        __z: float = self.scale.render_half_height - (z - self.scale.universe_center_z) * self.scale.scale_z
        shape = [(__x - SOLAR_SYSTEM_FATNESS, __z - SOLAR_SYSTEM_FATNESS), (__x + SOLAR_SYSTEM_FATNESS, __z + SOLAR_SYSTEM_FATNESS)]
        __luminosity: int = int(LUMINOSITY_MIN_BOUND + (sqrt(luminosity) - self.scale.min_luminosity) * self.scale.scale_luminosity)
        self.img_draw.ellipse(shape, fill=(__luminosity, __luminosity, __luminosity))

    def draw_events_list(self, events):
        __x: int = self.scale.left_bound_of_events
        for (idx, e) in enumerate(events):
            __y: float = RENDER_HEIGHT - idx*RENDER_HEIGHT/NUMBER_OF_EVENTS - self.scale.fontsize
            self.img_draw.text((__x, __y), e[0], fill=e[1], font=self.events_font)

    def draw_date_caption(self, date: str):
        __x: float = self.scale.render_center_width + (self.scale.min_x - self.scale.universe_center_x) * self.scale.scale_x
        self.img_draw.text((__x, 10), date, fill=(140, 140, 140), font=self.date_font)


def render_base_image(cwd: str, out_dir: str, verbose: bool = False):
    sde_names = eve_sde_tools.read_converted(cwd, "invNames")
    if verbose:
        print("Read {} names in Universe".format(len(sde_names)))
    sde_positions = eve_sde_tools.read_converted(cwd, "fsdUniversePositions")
    if verbose:
        print("Read {} solar systems positions in Universe".format(len(sde_positions)))

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

    # создаём канцу на которой будет рисовать
    canvas = Image.new('RGB', (RENDER_WIDTH, RENDER_HEIGHT), 'black')
    img_draw = ImageDraw.Draw(canvas)
    # настраиваем шрифты, которым будем рисовать события даты и т.п.
    events_font = ImageFont.truetype("arial.ttf", render_scale.fontsize)
    date_font = ImageFont.truetype("arial.ttf", render_scale.fontsize)

    # генерируем рисовалку вселенной и корпоративных событий
    renderer: RenderUniverse = RenderUniverse(img_draw, render_scale, events_font, date_font)
    # генерируем базовый фон с нанесёнными на него звёздами Вселенной EVE
    for p in sde_positions.values():
        renderer.draw_solar_system(p[0], p[2], p[3])
    # наносим события на базовый фон
    events = [['Hello, Qandra Si', 'green'], ['glorden lost Rhea', (255, 60, 60)]]
    renderer.draw_events_list(events)
    # наносим дату на изображение
    renderer.draw_date_caption('2022-02-05')

    canvas.save('{}/base_image.png'.format(out_dir))

    del sde_positions
    del sde_names
