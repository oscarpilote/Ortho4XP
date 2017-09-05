#!/usr/bin/env python3

import os,sys
from PIL import Image,ImageFilter,ImageOps,ImageEnhance,ImageStat
import numpy
from matplotlib import pyplot
from math import log

# switch
do_plot=True

# constants
margin_below_1perc=3
margin_above_99perc=3
target_med_red=85
target_med_green=98
target_med_blue=78
max_stddev_red=52    # was 50
max_stddev_green=45  # was 43
max_stddev_blue=44   # was 42
target_saturation=50

test_dir=sys.argv[1]

max_samples= len(sys.argv)>=3 and int(sys.argv[2]) or 99

historgb=numpy.zeros(768,dtype=numpy.int)
histohsv=numpy.zeros(768,dtype=numpy.int)
meanrgb=numpy.zeros(3,dtype=numpy.float)
meanhsv=numpy.zeros(3,dtype=numpy.float)
varrgb=numpy.zeros(3,dtype=numpy.float)
varhsv=numpy.zeros(3,dtype=numpy.float)
sampled_pix=0
samples=0 

for f in set(os.listdir(test_dir)):
    try:
        imrgb=Image.open(os.path.join(test_dir,f))
        imhsv=imrgb.convert('HSV')
        test=numpy.array(imhsv)
        test=(test[:,:,2]<=250)*(test[:,:,1]<=230)
        this_sampled=numpy.sum(test)
        mask=Image.fromarray(255*test.astype(numpy.uint8)) 
        statrgb=ImageStat.Stat(imrgb,mask)
        stathsv=ImageStat.Stat(imhsv,mask)
        meanrgbnew=(sampled_pix*meanrgb+this_sampled*numpy.array(statrgb.mean))/(sampled_pix+this_sampled)
        meanhsvnew=(sampled_pix*meanhsv+this_sampled*numpy.array(stathsv.mean))/(sampled_pix+this_sampled)
        varrgb=(sampled_pix*(varrgb+(meanrgbnew-meanrgb)**2)+this_sampled*(numpy.array(statrgb.stddev)**2+(meanrgbnew-statrgb.mean)**2))/(sampled_pix+this_sampled)
        varhsv=(sampled_pix*(varhsv+(meanhsvnew-meanhsv)**2)+this_sampled*(numpy.array(stathsv.stddev)**2+(meanhsvnew-stathsv.mean)**2))/(sampled_pix+this_sampled)
        meanrgb=meanrgbnew
        meanhsv=meanhsvnew
        historgb+=numpy.array(imrgb.histogram())
        histohsv+=numpy.array(imhsv.histogram())
        samples+=1
        sampled_pix+=this_sampled
    except Exception as e:
        print(e)
        print("Error loading",f,"as an image")
    if samples>=max_samples: break
 
if do_plot:
    pyplot.plot(histohsv[3:253],'r')
    pyplot.plot(histohsv[259:509],'g')
    pyplot.plot(histohsv[515:765],'b')

red_rep=numpy.cumsum(historgb[3:253])  # ! we eliminate extreme values (e.g. white no data imagery) from the statistics on purpose
red_rep=red_rep/red_rep[-1]
green_rep=numpy.cumsum(historgb[259:509]) # same
green_rep=green_rep/green_rep[-1]
blue_rep=numpy.cumsum(historgb[515:765]) # same
blue_rep=blue_rep/blue_rep[-1]
hue_rep=numpy.cumsum(histohsv[3:253])  
hue_rep=hue_rep/hue_rep[-1]
saturation_rep=numpy.cumsum(histohsv[259:509]) # same on both sides
saturation_rep=saturation_rep/saturation_rep[-1]
value_rep=numpy.cumsum(histohsv[515:765])
value_rep=value_rep/value_rep[-1]

sm=(saturation_rep>=0.5).argmax()+3
means=numpy.round(meanrgb)
stddevs=numpy.round(numpy.sqrt(varrgb))
print("Mean values (RGB HSV)",means,numpy.round(meanhsv))
print("Stddev values (RGB HSV)",stddevs,numpy.round(numpy.sqrt(varhsv)))
print("Median saturation : ",sm)
print("Median value :",(value_rep<=0.5).argmin())
print("Triples of 1 , 50 (median) and 99 percentiles:")
r1,rm,r99= [(red_rep>=x).argmax()+3 for x in (0.003,0.5,0.997)]
g1,gm,g99= [(green_rep>=x).argmax()+3 for x in (0.003,0.5,0.997)]
b1,bm,b99= [(blue_rep>=x).argmax()+3 for x in (0.003,0.5,0.997)]
print("red   : ", (r1,rm,r99))
print("green : ", (g1,gm,g99))
print("blue  : ", (b1,bm,b99))



ra=max(r1-margin_below_1perc,0)
rb=min(r99+margin_above_99perc,255) 
#rgamma=log((rm-ra)/(rb-ra))/log(target_med_red/255)
ga=max(g1-margin_below_1perc,0)
gb=min(g99+margin_above_99perc,255) 
#ggamma=log((gm-ga)/(gb-ga))/log(target_med_green/255)
ba=max(b1-margin_below_1perc,0)
bb=min(b99+margin_above_99perc,255) 
#bgamma=log((bm-ba)/(bb-ba))/log(target_med_blue/255)

mean_lightness=(rm+gm+bm)/3
mean_target_lightness=(target_med_red+target_med_green+target_med_blue)/3
delta_lightness=mean_lightness-mean_target_lightness
this_med_red=target_med_red+delta_lightness
this_med_green=target_med_blue+delta_lightness
this_med_blue =target_med_blue+delta_lightness



print("Recommended filters for the Ortho4XP color_filters section of that imagery :")
#print("rgb=",ra,rb,'{:.2f}'.format(rgamma),ga,gb,'{:.2f}'.format(ggamma),ba,bb,'{:.2f}'.format(bgamma))
ctrr=target_med_red/(rm-ra)
print(ctrr)
ctrr=min(ctrr,(255-this_med_red)/(rb-rm))
print(ctrr)
ctrr=min(ctrr,max_stddev_red/stddevs[0])
print(ctrr)
ctrg=target_med_green/(gm-ga)
print(ctrg)
ctrg=min(ctrg,(255-this_med_green)/(gb-gm))
print(ctrg)
ctrg=min(ctrg,max_stddev_green/stddevs[1])
print(ctrg)
ctrb=target_med_blue/(bm-ba)
print(ctrb)
ctrb=min(ctrb,(255-this_med_blue)/(bb-bm))
print(ctrb)
ctrb=min(ctrb,max_stddev_blue/stddevs[2])
print(ctrb)

rA=rm-target_med_red/ctrr
if rA<0: rA=-1*(this_med_red-ctrr*rm)
gA=gm-target_med_green/ctrg
if gA<0: gA=-1*(this_med_green-ctrg*gm)
bA=bm-target_med_blue/ctrb
if bA<0: bA=-1*(this_med_blue-ctrb*bm)
rB=rm+(255-this_med_red)/ctrr
if rB>255: rB=-1*(this_med_red+ctrr*(255-rm))
gB=gm+(255-this_med_green)/ctrg
if gB>255: gB=-1*(this_med_green+ctrg*(255-gm))
bB=bm+(255-this_med_blue)/ctrb
if bB>255: bB=-1*(this_med_blue+ctrb*(255-bm))

print("rgb=",tuple([round(x) for x in [rA,rB,gA,gB,bA,bB]]))
print("saturation=",'{:.2f}'.format(target_saturation/sm))
print("brightness=",'{:.2f}'.format(mean_target_lightness/mean_lightness))

if do_plot: pyplot.show()




        
