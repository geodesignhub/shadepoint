function uuidv4() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
    (
      +c ^
      (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))
    ).toString(16),
  );
}

function get_building_shadow(shadow_download_url) {
  fetch(shadow_download_url)
    .then((response) => {
      return response.json();
    })
    .then((shadow_data) => {
      if (shadow_data["features"].length > 0) {
        let spinner_cont = document.getElementById("spinner");
        spinner_cont.classList.add("d-none");
        let shadows_to_render = shadow_data;
        map.getSource("building_shadows").setData(shadows_to_render);
      } else {
        console.log("Shadow computation ongoing...");
        new Notify({
          status: "info",
          title: "Not completed",
          text: "Shadows are still being generated, check after 10 - 30 seconds",
          effect: "fade",
          speed: 300,
          customClass: "",
          customIcon: "",
          showIcon: true,
          showCloseButton: true,
          autoclose: true,
          autotimeout: 3000,
          notificationsGap: null,
          notificationsPadding: null,
          type: "outline",
          position: "bottom center",
          customWrapper: "",
        });
      }
    })
    .catch((error) => {
      console.log(error);
    });
}

function get_drawn_trees_shadows(drawn_trees_download_url) {
  fetch(drawn_trees_download_url)
    .then((response) => {
      return response.json();
    })
    .then((shadow_data) => {
      let spinner_cont = document.getElementById("shadow_spinner");
      spinner_cont.classList.add("d-none");
      let shadows_to_render = shadow_data;
      shadows_to_render = JSON.parse(shadows_to_render);
      let area = turf.area(shadows_to_render);
      //update the drawn_trees_shadow_area text with this in m2
      let drawn_trees_shadow_area = document.getElementById(
        "drawn_trees_shadow_area",
      );

      drawn_trees_shadow_area.innerHTML = "";
      let marked_element = document.createElement("mark");
      marked_element.innerHTML = area.toFixed(2) + "m2";
      drawn_trees_shadow_area.appendChild(marked_element);

      map.getSource("tree_shadows").setData(shadows_to_render);
      if (shadows_to_render["features"]) {
        tree_editing_control.shadows_loaded();
      } else {
        tree_editing_control.empty_shadows_loaded();
      }
      // map.getSource('existing_building_shadows').setData(shadows_to_render);
    })
    .catch((error) => {
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
      map.getSource("bike_pedestrian_roads").setData(roads_data);
    })
    .catch((error) => {
      console.log(error);
    });
}
function get_road_shadow_stats(roads_shadow_stats_url) {
  fetch(roads_shadow_stats_url)
    .then((response) => {
      return response.json();
    })
    .then((roads_shadow_data) => {
      let shadow_stats_cont = document.getElementById("shadow_stats");
      shadow_stats_cont.classList.remove("d-none");
      let total_roads = document.getElementById("total_roads");
      total_roads.innerHTML = roads_shadow_data["total_roads_kms"];

      let shadowed_roads = document.getElementById("shadowed_roads");
      shadowed_roads.innerHTML = roads_shadow_data["shadowed_kms"];
      let total_building_shadow_cont =
        document.getElementById("building_shadows");
      total_building_shadow_cont.innerHTML =
        roads_shadow_data["total_shadow_area"];
      if (roads_shadow_data["job_id"] !== "0000") {
        //  hide the get design shadows control
        let get_design_shadows = document.getElementById("get_shadows_control");
        get_design_shadows.classList.add("d-none");
      }
    })
    .catch((error) => {
      console.log(error);
    });
}

function get_existing_buildings_road_shadow_stats(roads_shadow_stats_url) {
  fetch(roads_shadow_stats_url)
    .then((response) => {
      return response.json();
    })
    .then((roads_shadow_data) => {
      let shadow_stats_cont = document.getElementById(
        "existing_buildings_shadow_stats",
      );
      shadow_stats_cont.classList.remove("d-none");
      let total_roads = document.getElementById(
        "existing_buildings_total_roads",
      );
      total_roads.innerHTML = roads_shadow_data["total_roads_kms"];

      let shadowed_roads = document.getElementById(
        "existing_buildings_shadowed_roads",
      );
      shadowed_roads.innerHTML = roads_shadow_data["shadowed_kms"];
    })
    .catch((error) => {
      console.log(error);
    });
}
