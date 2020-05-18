//https://leaflet-extras.github.io/leaflet-providers/preview/
var esri1  = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {attribution: 'Tiles &copy; Esri'}),
    esri2  = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {attribution: 'Tiles &copy; Esri'}),
    osm1   = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'}),
    osm2   = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'}),
    sat1   = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {attribution: 'Tiles &copy; Esri'});
    sat2   = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {attribution: 'Tiles &copy; Esri'});

//Défintion des layers pour le contrôleur de couches de la map1
var baseLayers1 = {
  "ESRI": esri1,
  "OSM": osm1,
  "Images satellites" : sat1
};
//Défintion des layers pour le contrôleur de couches de la map2
var baseLayers2 = {
  "ESRI": esri2,
  "OSM": osm2,
  "Images satellites" : sat2
};

//Instanciation de l'objet map1
var map1 = L.map('map1', {
  layers: [osm1]
}).setView([48.8392, 2.5876], 14);
//Instanciation de l'objet map2
var map2 = L.map('map2', {
  zoomControl: false,
  layers: [sat2]
}).setView([48.8392, 2.5876], 14);

//Fonction qui récupère l'extension d'un fichier
function getExtension(chemin){
   var regex = /[^.]*$/i;
   var resultats = chemin.match(regex);
   return resultats[0];
}

//Retourne l'élément 'input' du DOM à partir de son identifiant
var input = document.getElementById('input');

//Ecouter l'événement "change" de l'élément input
input.addEventListener("change", function(event) {
  var file = event.target.files[0];
  var name = file.name;
  var ext = getExtension(name).toLowerCase();

  //Si l'extension de fichier est "json" ou "geoJson", le polygon est ajouté aux deux contrôleurs de couches
  if (ext == "json" || ext == "geojson") {
      var reader = new FileReader();
      // Read the file
      reader.readAsText(file);
      // Invoked when file is loading.
      reader.onload = function(){
          // parse file to JSON object
          var jsonObject = reader.result;
          var json = JSON.parse(jsonObject);
          jsonlayer = L.geoJson(json, {
            onEachFeature: function (feature, layer) {
              layer.bindPopup("<br> Rayon de calcul : "+feature.properties.radius+"m");
            }
          });
          map1.fitBounds(jsonlayer.getBounds());
          var jsonLayerGroup = L.layerGroup().addLayer(jsonlayer);
          controls1.addOverlay(jsonLayerGroup, name);
          controls2.addOverlay(jsonLayerGroup, name);
      };

    //Si l'extension de fichier est "gpkg", l'extension de fichier n'est pas encore supportée
    }else if (ext == "gpkg") {
      // L.geoPackageTileLayer({
      //     geoPackageUrl: '',
      //     layerName: ''
      // }).addTo(map1);

      // L.geoPackageFeatureLayer([], {
      //     geoPackageUrl: '',
      //     layerName: ''
      // }).addTo(map1);
      alert("extension de fichier non supporté");

    //Si l'extension de fichier est "tif", le raster est ajouté aux deux contrôleurs de couches
    }else if (ext == "tif") {
      var reader = new FileReader();
      reader.readAsArrayBuffer(file);
      reader.onloadend = function() {
        var arrayBuffer = reader.result;
        parseGeoraster(arrayBuffer).then(georaster => {
          var layer = new GeoRasterLayer({
              georaster: georaster,
              opacity: 0.7,
              //La résolution peut servir à réduire le temps d'affichage
              resolution: 100
          });
        map1.fitBounds(layer.getBounds());
        var tifLayerGroup = L.layerGroup().addLayer(layer);
        controls1.addOverlay(tifLayerGroup, name);
        controls2.addOverlay(tifLayerGroup, name);
      });
    };

  //Si les autres extensions de fichier ne sont pas encore supportées
  }else {
    alert("extension de fichier non supporté");
  }
});


var overlays = {};
//Ajout des fonds de carte au contrôleur des calques
var controls1 = new L.control.layers(
	baseLayers1, overlays,
	{
		autoZIndex: false
	}).addTo(map1);

var controls2 = new L.control.layers(
	baseLayers2, overlays,
	{
		autoZIndex: false
	}).addTo(map2);

//Ajout de la fonction Fullscreen aux cartes
map1.addControl(new L.Control.Fullscreen({ position: 'bottomleft' }));
map2.addControl(new L.Control.Fullscreen({ position: 'bottomleft' }));
//Synchronisation des cartes
map1.sync(map2);
map2.sync(map1);


//Fonction qui crée un diagramme circulaire
function pie(ctx, w, h, datalist){
  var radius = h / 2 - 5;
  var centerx = w / 2;
  var centery = h / 2;
  var total = 0;
  for(x=0; x < datalist.length; x++) { total += datalist[x]; };
  var lastend=0;
  var offset = Math.PI / 2;
  for(x=0; x < datalist.length; x++){
    var thispart = datalist[x];
    ctx.beginPath();
    var colist = new Array('black', 'white');
    ctx.fillStyle = colist[x];
    ctx.moveTo(centerx,centery);
    var arcsector = Math.PI * (2 * thispart / total);
    ctx.arc(centerx, centery, radius, lastend - offset, lastend + arcsector - offset, false);
    ctx.lineTo(centerx, centery);
    ctx.fill();
    ctx.stroke();
    ctx.closePath();
    lastend += arcsector;
  }
}


//Instanciation du tableau statistique avec les entêtes de colonnes
var monTableau = [["Nom du fichier", "Pixels vus", "Pixels non vus", "Pourcentage de pixels vus", "Diagramme"]];
//Ecoute l'événement "change" de l'élément input, et lance une fonction asynchrone
input.onchange = async function(event) {
  var file = event.target.files[0];
  var name = file.name;
  var ext = getExtension(name).toLowerCase();
  //Si l'extension de fichier est "tif"
  if (ext == "tif") {
    const tiff = await GeoTIFF.fromBlob(input.files[0]);
    const image = await tiff.getImage();
    //data est la matrice contenant tous les valeurs de pixels
    const data = await image.readRasters({ interleave: true });
    //Récupére les infos statistiques
    var count0 = 0;   //Pixels non vus
    var count1 = 0;   //Pixels vus
    var noData = 0;   //Pixels no data (du à la projection)
    for (var i = 0; i < data.length; i++) {
      if (data[i] =="0") {
        count0 += 1;
      }else if (data[i] =="1") {
        count1 += 1;
      }else {
        noData += 1;
      }
    }
    //total est le nombre de pixels de l'image, sans compter les nodata
    var total = count0+ count1;
    //pourcentage du nombre de pixels vus par rapport au nombre total de pixels
    var pourcentage = (count1*100)/total;
    var pourcentage_arrondi = Math.round(pourcentage * 10000) / 10000 +"%"

    // console.log("Nom du fichier : " + name);
    // console.log("Pixels vus : " + count1);
    // console.log("Pixels non vus : " + count0);
    // console.log("No data : " + noData);
    // console.log("Nombre total de pixels : " + total);
    // console.log("Pourcentage pixels vus : " + pourcentage_arrondi);

    //Ajoute les valeurs statistiques dans un tableau intermédiaire
    var newTab = [name, count1, count0, pourcentage_arrondi];
    //Ajoute ce tableau intermédiaire à celui contenant les entêtes
    monTableau.push(newTab);

    //Crée un élément tableau HTML
    var table = document.createElement("TABLE");
    table.border = "1";
    //Récupère le nombre de colonnes
    var columnCount = monTableau[0].length;
    //Ajoute la ligne d'en-tête
    var row = table.insertRow(-1);
    for (var i = 0; i < columnCount; i++) {
        var headerCell = document.createElement("TH");
        headerCell.innerHTML = monTableau[0][i];
        row.appendChild(headerCell);
    }
    //Ajoute les lignes de données
    for (var i = 1; i < monTableau.length; i++) {
      row = table.insertRow(-1);
      for (var j = 0; j < columnCount; j++) {
        var cell = row.insertCell(-1);
        if (j==columnCount-1) {
          //Crée un canvas dans la dernière case de chaque ligne du tableau
          cell.innerHTML = '<canvas id="canvas'+i+'"></canvas>';
        }else {
          cell.innerHTML = monTableau[i][j];
        }
      }
    }
    //Supprime le logo VisionParCas puis insert le nouveau tableau
    document.getElementById("entetedroite").innerHTML = "";
    var dvTable = document.getElementById("stat");
    dvTable.innerHTML = "<h2>Comparaison statistique :</h2>";
    dvTable.appendChild(table);

    //Boucle qui remplit les canvas du tableau par les diagrammes circulaires
    for (var i = 1; i < monTableau.length; i++) {
      var canvas = document.getElementById("canvas"+i);
      var ctx = canvas.getContext('2d');
      var datalist= new Array(monTableau[i][2], monTableau[i][1]);
      var test = pie(ctx, canvas.width, canvas.height, datalist);
    };
  };
};
