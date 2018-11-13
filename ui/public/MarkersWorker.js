importScripts('https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.1.0/socket.io.js');

let parkingSocket;

/**
 * Both parked and moving states of cars are managed and updated in a dictionary.
 * Latest messages are sent through the WebSocket. 
 */
onmessage = (e) => {
    let cars = {
        parked: {},
        moving: {}
    };

    let anomalyCars;
    let msgcount = 0

    if (e.data[2].endsWith('#/garage')) {
        if (parkingSocket !== undefined) {
            parkingSocket.close();
        }

        parkingSocket = new WebSocket(e.data[0]);
        parkingSocket.onopen = (event) => {
            parkingSocket.send(e.data[1]);
        };

        parkingSocket.onmessage = (event) => {
            let streamData = JSON.parse(event.data);
            let newCars = streamData.data.cars.map((car) => {
                if (car.state !== 'moving' && car.sensorType === 'Camera') {
                    msgcount += 1
                };
                return car;
            });

            if (newCars.length !== 0) {
                /* this is not the first incoming data */
                let savedCars = { parked: {}, moving: {} };
                savedCars.parked = Object.assign({}, cars.parked);
                savedCars.moving = Object.assign({}, cars.moving);
                /* iterate through new coming data */
                for (let i = 0; i < newCars.length; i++) {

                    let stateID;

                    if (newCars[i].state === 'moving') {
                        stateID = newCars[i].id;
                        if (newCars[i].removed == 0) {
                            savedCars.moving[stateID.toString()] = newCars[i];
                        } else {
                            if (savedCars.moving.hasOwnProperty(stateID.toString())) {
                                delete savedCars.moving[stateID.toString()];
                            }
                        }
                    }
                    else if (newCars[i].state === 'parked') {
                        stateID = newCars[i].parkingSpot;
                        savedCars.parked[stateID.toString()] = newCars[i];
                    }
                    else if (newCars[i].state === 'empty') {
                        stateID = newCars[i].parkingSpot;
                        if (savedCars.parked.hasOwnProperty(stateID.toString())) {
                            delete savedCars.parked[stateID.toString()];
                        }
                    }
                }
                cars = savedCars;

                /* loop through savedCars to get updateCars object which needs to be passed back */
                let updateCars = {};

                Object.entries(savedCars.moving).forEach(([key, value]) => {
                    updateCars[key] = value;
                });

                Object.entries(savedCars.parked).forEach(([key, value]) => {
                    updateCars[key] = value;
                });


                postMessage(updateCars);

            }
        }

        parkingSocket.onerror = (event) => {
            console.log('[WEBSOCKET ERR]');
        }

        parkingSocket.onclose = (event) => {
            console.log('[WEBSOCKET CLOSE]');
        }

    }
};


