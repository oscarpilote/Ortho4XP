# Credit to Harry Otter for the default ScenProc script!
IMPORTOGR|@0@|*|building;landuse;natural;leisure|NOREPROJ
#
SplitGrid|AGN|*|building="*"
#
SETAGNBUILDINGHEIGHT|*|1.0;0.5;0.0;0.0
#creation de la vegetation
CreateAGNPolyVeg|FTYPE="POLYGON" And landuse="forest"|{0053b63d-b2c0-4bd9-9853-d9d21c9ad1fa}
CreateAGNPolyVeg|FTYPE="POLYGON" And natural="scrub"|{2fde0277-1697-4dab-b481-c3985c80596f}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And landuse="orchard"|{56a4998d-c1e5-416c-a37b-c35ce16504b6}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And landuse="conservation"|{bc6396b0-6e51-4a4f-ab4f-5386c84609a6}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And natural="wood"|{dcf543b7-c0d5-4fd4-b970-83965c2911c9}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And leisure="nature_reserve"|{82f0282d-f82d-484c-a640-aac21a69be03}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And leisure="garden"|{2368c260-177d-4af7-94d4-da882778108f}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And natural="tree"|{7dc6ef4e-92a5-4d0d-b94b-212dd1fa936d}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And natural="tree_row"|{a4a30975-075c-49ec-87fb-7e0931cb5004}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And natural="wetland"|{89ed8548-e54f-40ef-9837-7653885d409c}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And leisure="park"|{e04669c0-9f7b-42e8-a2c7-eee870c59d8e}
CREATEAGNPOLYVEG|FTYPE="POLYGON" And leisure="golf"|{2fbf9f8d-6ba2-4cc1-8d8e-af218f65d0e8}
# Add attribute to indicate the type of building
# 1 = ALMOST RECTANGLE (BASED ON AREA RATIO)
# 3 = REGULAR SHAPED (MANY PARALLEL EDGES)
# 4 = CONVEX POLYGONS
# 5 = CONCAVE POLYGONS
AddAttribute|FTYPE="POLYGON" And building="*"|Integer;BUILDTYPE|5
AddAttribute|FTYPE="POLYGON" And building="*" And BUILDTYPE=5 And FAREARAT>0.80|Integer;BUILDTYPE|1
AddAttribute|FTYPE="POLYGON" And building="*" And BUILDTYPE=5 And FNUMVERT<10 And FNUMPERPANG>3 And FNUMNOTPAR<2|Integer;BUILDTYPE|3
AddAttribute|FTYPE="POLYGON" And building="*" And BUILDTYPE=5 And FCONVEX=1|Integer;BUILDTYPE|4
# Classify industrial/commercial buildings
AddAttributeIfInside|FTYPE="POLYGON" And building="*"|LUCODE=16|String;BUILDCAT|INDUSTRIAL
AddAttributeIfInside|FTYPE="POLYGON" And building="*"|LUCODE=15|String;BUILDCAT|COMMERCIAL
# Add attribute for roof type
AddAttribute|FTYPE="POLYGON" And building="*" And FWIDTH>5|String;ROOFTYPE|PEAKED_ALL
AddAttribute|FTYPE="POLYGON" And building="*" And FWIDTH>5 And FLENGTH<12|String;ROOFTYPE|PEAKED_SIMPLE
AddAttribute|FTYPE="POLYGON" And building="*" And FWIDTH>20|String;ROOFTYPE|PEAKED_LOW_PITCH
AddAttribute|BUILDCAT="INDUSTRIAL"|String;ROOFTYPE|PEAKED_LOW_PITCH
AddAttribute|BUILDCAT="COMMERCIAL"|String;ROOFTYPE|PEAKED_LOW_PITCH
# Remove complex buildings
ReplacePolygonByBuildingRectangles|BUILDTYPE=3|0.8;4;4|0.25;2.0;0.5|Integer;BUILDTYPE|2
# Create buildings autogen
CreateAGNGenBuild|BUILDTYPE<3 And ROOFTYPE="PEAKED_ALL"|{c05c5106-d562-4c23-89b8-a4be7495b57c}|MAXRATIO=2
CreateAGNGenBuild|BUILDTYPE<3 And ROOFTYPE="PEAKED_SIMPLE"|{d4ee02a2-ed47-4f10-b98c-502516983383}
CreateAGNGenBuild|BUILDTYPE<3 And ROOFTYPE="PEAKED_LOW_PITCH"|{a9b0e686-0758-4294-a760-9bb4fd341621}
#
CreateAGNGenBuild|building="*" And FWIDTH<20|{5ae04eb6-934c-4f63-bb48-5e7dee601212}|MAXRATIO=2
CreateAGNGenBuild|building="*" And FWIDTH>20|{6089A0BD-CED1-4c47-9A9E-64CDD0E16983}
#
EXPORTAGN|FSX|@1@