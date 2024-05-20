
function get_existing_shadow_profile(bounds, session_id, shadow_datetime){

        
    let url = window.location.origin + '/compute_existing_building_stats?bounds=' + bounds+ '&session_id=' +session_id+'&shadow_datetime='+shadow_datetime;
    fetch(url)
        .then((response) => {
            return response.json();
        })
        .then((success_data) => {
            console.log("OK")
        }).catch((error) => {
            console.log(error);
        });
}


function get_building_shadow(shadow_download_url) {
    fetch(shadow_download_url)
        .then((response) => {
            return response.json();
        })
        .then((shadow_data) => {
            let spinner_cont = document.getElementById('spinner');
            spinner_cont.classList.add('d-none');

            let shadows_to_render = shadow_data;
            map.getSource('building_shadows').setData(shadows_to_render);
        }).catch((error) => {
            console.log(error);
        });
}



function get_existing_building_shadow(shadow_download_url) {
    
    fetch(shadow_download_url)
        .then((response) => {
            return response.json();
        })
        .then((shadow_data) => {
            let spinner_cont = document.getElementById('spinner');
            spinner_cont.classList.add('d-none');                
            let shadows_to_render = shadow_data;
            // map.getSource('existing_building_shadows').setData(shadows_to_render);
        }).catch((error) => {
            console.log(error);
        });
}

function get_downloaded_tree_canpoy(trees_url) {

    fetch(trees_url)
        .then((response) => {
            return response.json();
        })
        .then((trees_data) => {
            // let spinner_cont = document.getElementById('spinner');
            // spinner_cont.classList.add('d-none');

            let trees_to_render = trees_data;
            
            map.getSource('tree_canopy').setData(trees_to_render);
            
        }).catch((error) => {
            console.log(error);

        });
    }

function get_downloaded_roads(roads_url) {

    fetch(roads_url)
        .then((response) => {
            return response.json();
        })
        .then((roads_data) => {
            // let spinner_cont = document.getElementById('spinner');
            // spinner_cont.classList.add('d-none');

            // let roads_to_render = roads_data;   ds_data);             
            map.getSource('bike_pedestrian_roads').setData(roads_data);
        }).catch((error) => {
            
            console.log(error);
            
        });
    }
function get_road_shadow_stats(roads_shadow_stats_url) {

    fetch(roads_shadow_stats_url)
        .then((response) => {
            return response.json();
        })
        .then((roads_shadow_data) => {  
            let shadow_stats_cont = document.getElementById('shadow_stats');
            shadow_stats_cont.classList.remove('d-none');                
            let total_roads = document.getElementById('total_roads');
            total_roads.innerHTML = roads_shadow_data['total_roads_kms'];
            
            let shadowed_roads = document.getElementById('shadowed_roads');
            shadowed_roads.innerHTML = roads_shadow_data['shadowed_kms']
            let total_building_shadow_cont = document.getElementById('building_shadows');
            total_building_shadow_cont.innerHTML = roads_shadow_data['total_shadow_area'];
            
        }).catch((error) => {
            
            console.log(error);
            
        });
}

function get_existing_buildings_road_shadow_stats(roads_shadow_stats_url) {

    fetch(roads_shadow_stats_url)
        .then((response) => {
            return response.json();
        })
        .then((roads_shadow_data) => {                
            let shadow_stats_cont = document.getElementById('existing_buildings_shadow_stats');
            shadow_stats_cont.classList.remove('d-none');                
            let total_roads = document.getElementById('existing_buildings_total_roads');
            total_roads.innerHTML = roads_shadow_data['total_roads_kms'];
            
            let shadowed_roads = document.getElementById('existing_buildings_shadowed_roads');
            shadowed_roads.innerHTML = roads_shadow_data['shadowed_kms']
            
        }).catch((error) => {
            
            console.log(error);
            
        });
}