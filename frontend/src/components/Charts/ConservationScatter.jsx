import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ConservationScatter = ({ data }) => {
    return (
        <ResponsiveContainer width="100%" height="90%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" dataKey="x" name="AF" tickFormatter={v => v.toExponential(0)} label={{ value: 'Frequency', position: 'bottom', offset: 0, fontSize: 10 }} tick={{ fontSize: 10 }} />
                <YAxis type="number" dataKey="y" name="PhyloP" label={{ value: 'PhyloP', angle: -90, position: 'insideLeft' }} tick={{ fontSize: 10 }} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                <Scatter name="Variants" data={data} fill="#8b5cf6" fillOpacity={0.6} />
            </ScatterChart>
        </ResponsiveContainer>
    );
};

export default ConservationScatter;
