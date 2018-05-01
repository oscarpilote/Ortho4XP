import requests
# If the http request form of a provider does not follow a regular pattern, or require a token, you can use code here to form it.

# might get some session tokens here


# list of affected provider_codes
custom_url_list=[] 

def custom_wms_request(bbox,width,height,provider):
    if provider['code']=='****':
        (xmin,ymax,xmax,ymin)=bbox
        # do something
        # url = ******
    # etc
    return url

def custom_tms_request(tilematrix,til_x,til_y,provider):
    if provider['code']=='****':
        # do something
        # url = ******
    # etc
    return url
