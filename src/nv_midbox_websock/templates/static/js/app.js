angular.module('landingApp', [])
.controller('landingController', ['$scope', function($scope) {

  ws = new WebSocket("ws://localhost:8080/userwebsocket");
  
  ws.onmessage = function(e) {
    console.log(e.data);
  };     

  // $scope.cameraInfo = [
  //   {
  //     id : 1,
  //     name: "Camera1",
  //     status: 0,
  //     description: "Baby room camera"
  //   },{
  //     id : 2,
  //     name: "Camera2",
  //     status: 1,
  //     description: "ICU room camera"
  //   },{
  //     id : 3,
  //     name: "Camera3",
  //     status: 1,
  //     description: "Hallway camera"
  //   },{
  //     id : 4,
  //     name: "Camera4",
  //     status: 0,
  //     description: "Incubator camera"
  //   },{
  //     id : 5,
  //     name: "Camera5",
  //     status: 1,
  //     description: "Bedside camera"
  //   },{
  //     id : 6,
  //     name: "Camera6",
  //     status: 1,
  //     description: "Test one"
  //   }
  // ];
}]);