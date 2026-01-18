import http from 'k6/http';
import { check } from 'k6';

export const options = {
  iterations: 10,
};

// The default exported function is gonna be picked up by k6 as the entry point for the test script. It will be executed repeatedly in "iterations" for the whole duration of the test.
export default function () {
  // Make a GET request to the target URL
  const response = http.get('https://api.worldofapps.bar/tasks/',{headers: { 'Authorization': 'Bearer 4dbe9625eafbc2bc7abcc345532d8fe11e7f0bc5' }});
  // http.post('https://api.worldofapps.bar/tasks/',{description: "k6 testing"},{headers: { 'Authorization': 'Bearer 4dbe9625eafbc2bc7abcc345532d8fe11e7f0bc5' }});

  check(response, {
    'response code was 200': (response) => response.status == 200,
  });
}
