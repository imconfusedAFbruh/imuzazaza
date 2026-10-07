from pathlib import Path
from PIL import Image,ImageDraw
import json
ROOT=Path(__file__).resolve().parent
source=ROOT/'outputs_clock_routes_v44/figures'
out=ROOT/'tmp/pdfs/research_window_v38/final_contacts'
out.mkdir(parents=True,exist_ok=True)
files=sorted(source.glob('*.png'))
for first in range(0,len(files),6):
    canvas=Image.new('RGB',(1560,1065),'white');draw=ImageDraw.Draw(canvas)
    for index,path in enumerate(files[first:first+6]):
        with Image.open(path) as im:
            im.thumbnail((780,345));x=(index%2)*780;y=(index//2)*355
            canvas.paste(im,(x,y));draw.text((x+5,y+342),f'{first+index+1}: '+path.stem,fill='black')
    canvas.save(out/f'contacts_{first//6+1:02}.png')
(out/'order.json').write_text(json.dumps([p.name for p in files],indent=2))
print(len(files),'figures',len(list(out.glob('*.png'))),'contacts')
