"""Convert WMA resources for one test to browser-compatible MP3, locally."""
import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.deps'))
from core import read_json,write_json


def main():
    import imageio_ffmpeg
    parser=argparse.ArgumentParser()
    parser.add_argument('test_id')
    args=parser.parse_args()
    catalog=read_json(ROOT/'data/catalog.json',{})
    sources=read_json(ROOT/'data/local_sources.json',{})
    test=next(t for t in catalog['tests'] if t['id']==args.test_id)
    archive=ROOT/'.bingo'/(args.test_id+'-converted.zip')
    source=args.test_id+'-converted'
    converted=[]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for rid in test['resources']:
            r=catalog['resources'][rid]
            if r['ext']!='.wma':
                continue
            with zipfile.ZipFile(sources[r['source']]) as original:
                raw=original.read(r['entry'])
            result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-i','pipe:0','-vn','-codec:a','libmp3lame','-q:a','3','-f','mp3','pipe:1'],input=raw,capture_output=True,check=True)
            name=Path(r['name']).stem+'.mp3'
            output.writestr(name,result.stdout)
            r.update(source=source,entry=name,name=name,ext='.mp3',size=len(result.stdout))
            converted.append(rid)
    sources[source]=str(archive)
    write_json(ROOT/'data/catalog.json',catalog)
    write_json(ROOT/'data/local_sources.json',sources)
    print(f'Converted {len(converted)} WMA tracks to MP3; original ZIP unchanged.')


if __name__=='__main__':
    main()
