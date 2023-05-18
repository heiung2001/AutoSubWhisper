import os
import pysrt
import whisper
import moviepy.editor as mp
import translators as ts

from pysrt import SubRipFile
from whisper.utils import get_writer
from collections import defaultdict as ddict


def extract_audio_from_video_folder(input_path: str,
                                    output_path: str) -> None:
    os.makedirs(output_path, exist_ok=True)

    for mp4_file in os.listdir(input_path):
        video = mp.VideoFileClip(input_path + mp4_file)
        audio = video.audio
        audio.write_audiofile(output_path + mp4_file[:-4] + '.mp3')


def transcribe(input_path: str,
               output_path: str,
               model_name: str = 'base') -> None:
    os.makedirs(output_path, exist_ok=True)

    model_path = "models/"
    model = whisper.load_model(model_name, download_root=model_path)
    writer = get_writer('srt', output_path)
    for audio in os.listdir(input_path):
        transcript = model.transcribe(input_path + audio)
        writer(transcript, input_path+audio, ddict(int))


def create_subtitle_clips(subtitles,
                          video_size,
                          font: str,
                          font_size: int = 24,
                          color: str = 'yellow') -> list:
    subtitle_clips = []
    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time   = time_to_seconds(subtitle.end)
        duration   = end_time - start_time

        video_width, video_height = video_size
        subtitle_x_position = 'center'
        subtitle_y_position = video_height * (4/5)
        text_position = (subtitle_x_position, subtitle_y_position)

        text_clip = mp.TextClip(subtitle.text, fontsize=font_size, font=font,
                                color=color, bg_color='black', size=(video_width*3/4, None),
                                method='caption').set_start(start_time).set_duration(duration)
        subtitle_clips.append(text_clip.set_position(text_position))
    return subtitle_clips


def translate_srt_file(input_file: str,
                       output_file: str,
                       to_language: str = 'en',
                       engine: str = 'google') -> None:
    subs = SubRipFile.open(input_file, encoding='utf-8')
    for sentence in subs:
        sentence.text = ts.translate_text(sentence.text, translator=engine, to_language=to_language)
    subs.save(output_file, encoding='utf-8')


def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000


def main():
    data_path  = "data/"
    video_path = data_path + 'video/'
    audio_path = data_path + 'audio/'
    srt_path   = data_path + 'srt/'
    sub_path   = data_path + 'subtitle/'

    # extract audio from mp4 files
    extract_audio_from_video_folder(video_path, audio_path)

    # write subtitle (chinese) to srt format
    transcribe(audio_path, srt_path, model_name='large')

    # translate chinese to vietnamese
    for file in os.listdir(srt_path):
        translate_srt_file(f'{srt_path}{file}', f'{srt_path}{file[:-4]}_translated.srt',
                           to_language='vi', engine='google')

    # insert subtitle to video
    mp4_list = sorted(os.listdir(video_path))
    srt_list = sorted(list(filter(lambda x: '_translated' in x, os.listdir(srt_path))))
    for mp4_file, srt_file in zip(mp4_list, srt_list):
        video    = mp.VideoFileClip(video_path + mp4_file)
        subtitle = pysrt.open(srt_path + srt_file, encoding='utf-8')

        name, _ = mp4_file.split('.mp4')
        output_video_file = name + '_subtitled.mp4'

        subtitle_clips = create_subtitle_clips(subtitle, video.size, font='FreeMono')
        final_video    = mp.CompositeVideoClip([video] + subtitle_clips)
        final_video.write_videofile(sub_path + output_video_file)


if __name__ == "__main__":
    main()
