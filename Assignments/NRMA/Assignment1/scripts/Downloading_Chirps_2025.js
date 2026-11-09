//CHIRPS Daily -> 12 monthly rainfall totals (mm) for Kasungu for 2025
// output  12 images to Google Drive

// ROI and buffered export box (10 km buffer, to prevent cuting of pixels)
//roi was imported from asssets
var exportBox = roi.geometry().buffer(10000).bounds();
Map.centerObject(roi, 8);
Map.addLayer(exportBox, {color: 'blue'}, 'Export box (buffered)', true, 0.3);
Map.addLayer(roi, {color: 'red'}, 'Kasungu ROI');

// daily rainfall  mm/day
var year = 2025;
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');

// Sanity checks (Console)
var yearDaily = chirps.filterDate(year + '-01-01', (year + 1) + '-01-01');
print('Daily images in ' + year + ' (expect 365):', yearDaily.size());
print('Annual mean rainfall over Kasungu (mm):',
  yearDaily.sum().reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: roi.geometry(),
    scale: 5566,
    maxPixels: 1e9
  }).get('precipitation'));

//  Monthly totals + one export task per month
for (var m = 1; m <= 12; m++) {
  var start = ee.Date.fromYMD(year, m, 1);
  var monthly = chirps
    .filterDate(start, start.advance(1, 'month'))
    .sum()                      // monthly TOTAL (mm), not mean
    .rename('P_mm')
    .toFloat();

  var mm = ('0' + m).slice(-2);

  Export.image.toDrive({
    image: monthly,
    description: 'chirps_' + year + '_' + mm,
    fileNamePrefix: 'chirps_' + year + '_' + mm,
    folder: 'Mapping-and-GIS',      
    region: exportBox,
    crs: 'EPSG:4326',
    crsTransform: [0.05, 0, -180, 0, -0.05, 50],  // keeps the native CHIRPS pixel grid
    maxPixels: 1e9,
    fileFormat: 'GeoTIFF'
  });
}