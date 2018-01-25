# In case of providers whose request do not follow a regular pattern, you can use code here to form it

# list of affected provider_codes
custom_url_list=[]

def custom_url_request(bbox,width,height,provider):
    if provider['code']=='****':
        (xmin,ymax,xmax,ymin)=bbox
        # do something
        # url=*****
    elif provider['code']=='****':
        (xmin,ymax,xmax,ymin)=bbox
        # do something
        # url = ******
    elif provider['code']=='****':
        (xmin,ymax,xmax,ymin)=bbox
        # do something
        # url = ******
    # etc
    return url
