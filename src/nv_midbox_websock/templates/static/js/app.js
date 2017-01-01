angular.module('landingApp', ['ngWebsocket'])
.controller('landingController', ['$scope', '$websocket', function($scope, $websocket) {

  var ws = $websocket.$new('ws://localhost:8080/userwebsocket');

  // ws.$on('$open', function () {
  //   ws.$emit('hello', 'world'); // it sends the event 'hello' with data 'world'
  // })
  ws.$on('onmessage', function (message) { // it listents for 'incoming event'
    console.log('something incoming from the server: ' + message);
  });

  $scope.cameraInfo = [
    {
      id : 1,
      name: "Camera1",
      status: 0,
      description: "Baby room camera"
    },{
      id : 2,
      name: "Camera2",
      status: 1,
      description: "ICU room camera"
    },{
      id : 3,
      name: "Camera3",
      status: 1,
      description: "Hallway camera"
    },{
      id : 4,
      name: "Camera4",
      status: 0,
      description: "Incubator camera"
    },{
      id : 5,
      name: "Camera5",
      status: 1,
      description: "Bedside camera"
    },{
      id : 6,
      name: "Camera6",
      status: 1,
      description: "Test one"
    }
  ];
  console.log("this is the controller");
}]);