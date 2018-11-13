import React from 'react';
import { FormGroup, ControlLabel, FormControl, Checkbox, Col, HelpBlock } from 'react-bootstrap';


const input = ({id, label, change, type, value, help}) => {
    let inputCol;
    switch(type) {
        case 'checkbox':
            inputCol = <Checkbox checked={value} onChange={(e)=>change(id, e.target.checked, e.target.validity.valid, 'input')} />;
            break;
        case 'number':
            inputCol = <FormControl type='number' step='0.000000000000001' value={value} onChange={(e)=>change(id, e.target.value, e.target.validity.valid, 'input')} />;
            break;
        default: 
            inputCol = <FormControl type={type} value={value} onChange={(e)=>change(id, e.target.value, e.target.validity.valid, 'input')} />;
    }

    return (
        <FormGroup controlId={id}>
            <Col componentClass={ControlLabel} sm={2}>{label}</Col>
            <Col sm={10}>
                {inputCol}
                {help && <HelpBlock>{help}</HelpBlock>}
            </Col>
        </FormGroup>
    );
};

export default input;