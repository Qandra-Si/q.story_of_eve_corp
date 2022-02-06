# Q.Story of EVE Corp

Генератор видео-мультфильмов на основе сведений, загруженных с серверов CCP, zKillboard и распакованных из Static ESI CCP. Модернизированная версия похожего генератора [show_alliance](https://github.com/Qandra-Si/show_alliance), но информация наносится на карту солнечных систем EVE Online. Отображаются PvP активности пилотов корпораций

*Результат работы генератора*

[![R Initiative 4 eveonline](https://img.youtube.com/vi/jwvHbyBFk0A/0.jpg)](https://youtu.be/jwvHbyBFk0A "R Initiative 4 eveonline")

Для изготовления мультфильма понадобится Python, [статический ESI](https://developers.eveonline.com/resource/resources), [генератор видео](https://www.ffmpeg.org/), подключение к Internet и терпение на несколько часов работы ЭВМ. Скорость работы программы зависит от настроек генерации видео, по умолчанию задана настройка Ultra HD 4K 3840×2160 с частотой 24 кадра в секунду.

Исходными данными для программы являются накопленные исторические данные, которые подаются на вход в .txt формате: см. примеры в файлах [events.txt](input/example/events-utf8.txt), [killmails.txt](input/example/killmails-utf8.txt), [industry_jobs.txt](input/example/industry_jobs-utf8.txt), [market.txt](input/example/market-utf8.txt). Данные могут быть получены автоматизированным способом из корпоративного Seat с помощью готовых запросов [queries.sql](input/example/queries.sql) для выполнения которых потребуются некоторые представления из репозитория [q.seat](https://github.com/Qandra-Si/q.seat).

## Инструкция по использованию

Установить Python 3, например отсюда https://virtualenv.pypa.io/en/stable/

Запустить с правами администратора установку требуемых дополнений:

```bash
pip install -r requirements.txt
```

Исправить настройки в файле render.py, например разрешение Ultra HD 4K 3840×2160 и частоту кадров 24 кадра в секунду.

```bash
chcp 65001 & @rem on Windows only!
python eve_sde_tools.py
python story_of_eve_corp.py -i ./input -o ./output -v
ffmpeg -i ./output/%05d.png -vf "scale=3840:2160,fps=24" video.mp4
```

Для добавления аудио трека в видео поток выполнить следующие команды (заранее подобрав аудио-файлы audio1.mp3, audio2.mp3 ... нужной длительности):

```bash
cat audiolist.txt
# file 'audio1.mp3'
# file 'audio2.mp3'
# file 'audio3.mp3'
ffmpeg -f concat -i audiolist.txt -c copy audio.mp3
ffmpeg -i video.mp4 -i audio.mp3 -codec:v copy -codec:a copy -shortest video-plus-audio.mp4
```
