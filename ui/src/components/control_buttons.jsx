import React, { Component } from "react";
import axios from "axios";

class ControlButton extends React.Component {
  constructor() {
    super();

    this.state = {
      food: "Chinese"
    };
  }

  handleSubmit(event) {
    const { food } = this.state;

    event.preventDefault();

    const options = {
      url: "http://localhost:4321/api/testcontrol",
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json;charset=UTF-8"
      },
      data: {
        run: true
      }
    };

    // do something with form values, and then
    axios(options).then(response => {
      console.log(response.status);
    });
  }

  render() {
    return (
      <div>
        <form method="post" onSubmit={event => this.handleSubmit(event)}>
          <p>
            I like <span name="food">{this.state.food}</span> ood
          </p>
          <button type="submit">Butane</button>
        </form>
      </div>
    );
  }
}

export default ControlButton;
